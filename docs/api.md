# API Reference — hivemind-ggwave

Source: `hivemind_ggwave/__init__.py`

All classes are threads (`Thread`) or thread wrappers. The `ggwave-rx` binary must be installed for any of them to function.

---

## `GGWave`

```python
class GGWave(Thread)
```

Low-level wrapper around the `ggwave-rx` subprocess. Continuously reads decoded payloads from the subprocess stdout and dispatches them to registered opcode handlers.

### Constructor

```python
GGWave(config=None, callbacks=None, debug=False)
```

| Parameter | Type | Description |
|---|---|---|
| `config` | `dict` | Optional config with `ggwave-rx` and `ggwave-cli` paths, and `remote` flag |
| `callbacks` | `dict` | Mapping of opcode prefix strings → handler callables |
| `debug` | `bool` | Log intermediate ggwave-rx output |

Config keys:
| Key | Description |
|---|---|
| `ggwave-rx` | Path to `ggwave-rx` binary (default: `~/.local/bin/ggwave-rx`) |
| `ggwave-cli` | Path to `ggwave-cli` binary (default: `~/.local/bin/ggwave-cli`) |
| `remote` | If `True`, encode audio via the web API instead of local `ggwave-cli` |

Raises `ValueError` if `ggwave-rx` is not found.

If `ggwave-cli` is not found, forces `remote=True`.

### `run()`

Spawns `ggwave-rx` via `pexpect` and reads stdout line by line. When a line matches `"Received sound data successfully: "`, extracts the payload and routes it to the matching opcode handler.

Opcode matching: the payload is checked against each key in `OPCODES`; the first matching prefix wins, and the remainder of the payload (after the prefix) is passed to the handler.

### `emit(payload)`

Transmit a string as a ggwave audio signal.

- **Local mode** (`remote=False`): spawns `ggwave-cli`, sends the payload interactively
- **Remote mode** (`remote=True`): calls `encode2wave()` to fetch a WAV from the ggwave web API, then plays it locally

### `encode2wave(message, wav_path, protocolId=1, sampleRate=48000, volume=50, payloadLength=-1, useDSS=0) -> str`

Encodes a message as a ggwave WAV file using the public web API at `https://ggwave-to-file.ggerganov.com/`. Writes the WAV to `wav_path` and returns the path.

| Parameter | Description |
|---|---|
| `protocolId` | Transmission protocol (0=audible, 1=audible fast, etc.) |
| `sampleRate` | Output sample rate (default 48000 Hz) |
| `volume` | Output volume 0–100 |
| `payloadLength` | Fixed-length encoding if positive; -1 = variable |
| `useDSS` | Enable Doppler Spread Sensing |

### `stop()`

Sets `running = False`. The `run()` loop exits at the next readline.

---

## `GGWaveMaster`

```python
class GGWaveMaster(Thread)
```

Hub-side GGWave pairing handler. Periodically broadcasts a password via audio; when a satellite responds with its access key, the master adds it to the `hivemind-core` client database and acknowledges with the hub host address.

### Constructor

```python
GGWaveMaster(bus=None, pswd=None, host=None, silent_mode=False, config=None,
             add_client_callback=None,
             ws_port=None, ws_ssl=False,
             http_port=None, http_ssl=False)
```

| Parameter | Type | Description |
|---|---|---|
| `bus` | `FakeBus` or `MessageBusClient` | OVOS bus for emitting events |
| `pswd` | `str` | Pre-set pairing password (auto-generated if `None`) |
| `host` | `str` | Hub IP to broadcast (auto-detected via `get_ip()` if `None`) |
| `silent_mode` | `bool` | If `True`, do not broadcast password — assume it is conveyed out-of-band |
| `config` | `dict` | Forwarded to `GGWave` |
| `add_client_callback` | `callable` or `None` | If set, called instead of `hivemind_core.ClientDatabase` — signature: `callback(access_key: str, pswd: str)` |
| `ws_port` | `int` or `None` | If set, emits `HMWSP:ws[s]://host:port` so satellites learn the WebSocket URL with port |
| `ws_ssl` | `bool` | Whether the WebSocket server uses SSL (`wss://`) |
| `http_port` | `int` or `None` | If set, emits `HMHTTP:http[s]://host:port` so satellites can use the HTTP protocol |
| `http_ssl` | `bool` | Whether the HTTP server uses SSL (`https://`) |

Registers opcode handler: `"HMKEY:" → handle_key`

### `run()`

1. Starts the `GGWave` thread
2. Emits `hm.ggwave.activated` on bus
3. Generates password and detects host if not provided
4. **Loop** (every 5 seconds, unless `silent_mode`):
   - Broadcasts `HMPSWD:<password>` via ggwave
   - Emits `hm.ggwave.pswd_emitted` on bus

### `handle_key(payload)`

Called when a satellite broadcasts `HMKEY:<access_key>`:

1. Emits `hm.ggwave.key_received`
2. Calls `add_client(access_key)` — adds to `hivemind-core` `ClientDatabase`
3. If `ws_port` is set: broadcasts `HMWSP:ws[s]://<host>:<ws_port>` via ggwave
4. If `http_port` is set: broadcasts `HMHTTP:http[s]://<host>:<http_port>` via ggwave
5. Broadcasts `HMHOST:<host>` via ggwave (always, for backward compatibility)
6. Emits `hm.ggwave.host_emitted`

### `add_client(access_key)`

Registers a new client. Two code paths:

1. **If `add_client_callback` is set** — calls `callback(access_key, self.pswd)`,
   then emits `hm.ggwave.client_registered` with `{key, pswd}`. No import of
   `hivemind_core` occurs. This is the recommended path when using GGWaveMaster
   outside of a standard `hivemind-core` hub.

2. **If `add_client_callback` is `None`** — imports and uses
   `hivemind_core.database.ClientDatabase` directly, adds:
   - `name`: `"HiveMind-Node-<N>"` (auto-numbered)
   - `api_key`: the received `access_key`
   - `crypto_key`: 8 random bytes (hex)
   - `password`: `self.pswd`

   Emits `hm.ggwave.client_registered` with `{key, pswd, id, name}`.

### `stop()`

Stops the `GGWave` thread and emits `hm.ggwave.deactivated`.

---

## `GGWaveSlave`

```python
class GGWaveSlave
```

Satellite-side GGWave pairing handler. Listens for a broadcast password, responds with a generated access key, and saves the received host to `NodeIdentity`.

### Constructor

```python
GGWaveSlave(key=None, bus=None, config=None)
```

| Parameter | Type | Description |
|---|---|---|
| `key` | `str` | Access key to register with the hub (auto-generated if `None`) |
| `bus` | `FakeBus` or `MessageBusClient` | OVOS bus for events |
| `config` | `dict` | Forwarded to `GGWave` |

Registers opcode handlers:
- `"HMPSWD:" → handle_pswd`
- `"HMWSP:" → handle_wsp`
- `"HMHTTP:" → handle_http`
- `"HMHOST:" → handle_host`

### `start()` / `stop()`

Start or stop the underlying `GGWave` thread.

### `handle_pswd(payload)`

Called when the master broadcasts `HMPSWD:<password>`:

1. Stores the password
2. Emits `hm.ggwave.pswd_received`
3. Broadcasts `HMKEY:<self.key>` back to the master
4. Emits `hm.ggwave.key_emitted`

### `_resolve_host(payload) -> str`

Override point for subclasses. Given the raw payload string from `HMHOST:`,
returns the URL that will be stored in `NodeIdentity.default_master`.

Default implementation returns `payload` unchanged. `GGWavePresenceSlave`
overrides this to substitute a pre-discovered URL that includes the correct port.

Only called by `handle_host()` — `handle_wsp()` and `handle_http()` use the
full URL from the opcode payload directly.

### `_save_identity(host)`

Normalises `host` to a URL (prepends `ws://` if no scheme), writes
`NodeIdentity` with `password`, `access_key`, and `default_master`, emits
`hm.ggwave.identity_updated`, and calls `stop()`. Shared by all three host
handlers.

### `handle_wsp(payload)`

Called when the master broadcasts `HMWSP:<url>` (e.g. `ws://192.168.1.1:5678`):

1. Emits `hm.ggwave.host_received`
2. Sets `_ws_url_received = True`
3. Calls `_save_identity(payload)`

Once this handler runs, any subsequent `HMHTTP:` or `HMHOST:` opcodes are ignored.

### `handle_http(payload)`

Called when the master broadcasts `HMHTTP:<url>` (e.g. `http://192.168.1.1:8080`).
Ignored if `_ws_url_received` is `True` (a WebSocket URL was already stored).

1. Emits `hm.ggwave.host_received`
2. Calls `_save_identity(payload)`

### `handle_host(payload)`

Called when the master broadcasts `HMHOST:<host>` (bare IP, legacy).
Ignored if `_ws_url_received` is `True`.

1. Calls `self._resolve_host(payload)` to get the final host URL
2. Emits `hm.ggwave.host_received`
3. Calls `_save_identity(resolved_host)`

---

## `GGWavePresenceSlave`

```python
class GGWavePresenceSlave(GGWaveSlave)
```

`GGWaveSlave` that pre-discovers the hub URL via **UPnP/Zeroconf** (using
`hivemind-presence`) before the GGWave pairing audio exchange begins. Requires
the optional `hivemind-presence` package; falls back to plain `GGWaveSlave` if
not installed.

### Constructor

```python
GGWavePresenceSlave(key=None, bus=None, config=None, presence_timeout=25.0)
```

| Parameter | Type | Description |
|---|---|---|
| `presence_timeout` | `float` | Seconds to scan for UPnP/Zeroconf nodes (default: `25.0`) |

### `start()`

1. Tries to import `hivemind_presence.LocalDiscovery`
2. Scans for HiveMind nodes for up to `presence_timeout` seconds
3. If a node is found, stores its WebSocket URL in `self._discovered_url`
4. Calls `super().start()` to begin GGWave listening

### `_resolve_host(payload) -> str`

Returns `self._discovered_url` if set, otherwise `payload` (bare IP from `HMHOST:`).

---

## Opcode protocol

| Direction | Opcode prefix | Payload | Meaning |
|---|---|---|---|
| Master → Satellite | `HMPSWD:` | pairing password | Hub broadcasting credentials |
| Satellite → Master | `HMKEY:` | access key | Satellite registering itself |
| Master → Satellite | `HMWSP:` | full WebSocket URL (`ws[s]://ip:port`) | Hub confirming registration — WebSocket endpoint |
| Master → Satellite | `HMHTTP:` | full HTTP URL (`http[s]://ip:port`) | Hub confirming registration — HTTP endpoint |
| Master → Satellite | `HMHOST:` | hub IP address (bare) | Hub confirming registration — legacy, no port |

The satellite applies the **first** host URL opcode it receives in priority order:
`HMWSP:` > `HMHTTP:` > `HMHOST:`. All three are emitted by `GGWaveMaster.handle_key()`
for maximum compatibility; older satellites that only understand `HMHOST:` will use it.

---

## Bus events

| Event | Emitter | Data |
|---|---|---|
| `hm.ggwave.activated` | Master and Slave | — |
| `hm.ggwave.deactivated` | Master and Slave | — |
| `hm.ggwave.pswd_emitted` | Master | — |
| `hm.ggwave.key_received` | Master | — |
| `hm.ggwave.host_emitted` | Master | — |
| `hm.ggwave.client_registered` | Master | `{key, pswd, id, name}` |
| `hm.ggwave.pswd_received` | Slave | — |
| `hm.ggwave.key_emitted` | Slave | — |
| `hm.ggwave.host_received` | Slave | — |
| `hm.ggwave.identity_updated` | Slave | — |
