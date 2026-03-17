# Master and Slave Implementations

`hivemind-ggwave` provides **primitives** — it defines the protocol opcodes
and the classes that implement them. Orchestration (when to start/stop, how to
display the pairing code, how to register clients) is the caller's
responsibility.

- **Source**: `hivemind_ggwave/__init__.py`

---

## `GGWaveMaster` — hub side

Manages password broadcasting and client registration.

### Normal mode

`GGWaveMaster.run()` — `hivemind_ggwave/__init__.py` — generates a random
password, starts the `GGWave` receiver, and broadcasts `HMPSWD:<password>`
every 5 seconds until stopped. When `HMKEY:` is received from a satellite,
`handle_key()` calls `add_client()` and broadcasts the hub URL(s) back.

### Silent mode (`silent_mode=True`)

The password is **not** broadcast automatically. `run()` logs the pairing code
and waits. The **caller** decides when and how to transmit it.

The intended flow in `hivemind-core`:
1. Orchestrator starts `GGWaveMaster(silent_mode=True)`.
2. UI shows `master.pswd` to the user (on screen, QR code, etc.).
3. User presses a button → orchestrator calls
   `master.ggwave.emit(f"HMPSWD:{master.pswd}")`.
4. Password is transmitted exactly once, on demand — safer than a continuous
   broadcast loop.

The browser tool at https://jarbashivemind.github.io/hivemind-ggwave is an
alternative: the hub shows the code, the user types it into the browser on
their phone, and the phone plays the audio. No hub speaker needed.

### Client registration

`add_client(access_key)` — `hivemind_ggwave/__init__.py` — has two paths:

- **`add_client_callback` set** — calls `callback(access_key, pswd)`. No
  dependency on `hivemind-core`. The caller handles persistence.
- **`add_client_callback=None`** — imports and uses
  `hivemind_core.database.ClientDatabase` directly (default, backward compat).

### Bus events emitted by `GGWaveMaster`

| Event | When |
|---|---|
| `hm.ggwave.activated` | `run()` starts |
| `hm.ggwave.pswd_emitted` | each broadcast cycle (normal mode only) |
| `hm.ggwave.key_received` | `HMKEY:` received from satellite |
| `hm.ggwave.client_registered` | client added |
| `hm.ggwave.host_emitted` | hub URL(s) sent back |
| `hm.ggwave.deactivated` | `stop()` called |

---

## `GGWaveSlave` — satellite side

Listens for the hub password, replies with its access key, then waits for the
hub address and saves `NodeIdentity`.

### Opcode priority

The satellite accepts the **first** host opcode it receives:
`HMWSP:` > `HMHTTP:` > `HMHOST:`. All three may arrive; older hubs that only
send `HMHOST:` are handled transparently.

### Extension points

- `_resolve_host(payload)` — override to substitute a pre-discovered URL for
  the bare IP in `HMHOST:` payloads.
- `_save_identity(host)` — normalises the URL, writes `NodeIdentity`, emits
  `hm.ggwave.identity_updated`, and calls `stop()`.

### Bus events emitted by `GGWaveSlave`

| Event | When |
|---|---|
| `hm.ggwave.activated` | `start()` called |
| `hm.ggwave.pswd_received` | `HMPSWD:` received |
| `hm.ggwave.key_emitted` | `HMKEY:` sent |
| `hm.ggwave.host_received` | any host opcode received |
| `hm.ggwave.identity_updated` | identity saved |
| `hm.ggwave.deactivated` | `stop()` called |

---

## `GGWavePresenceSlave`

Extends `GGWaveSlave` by scanning for the hub via `hivemind-presence`
(UPnP/Zeroconf/Beacon) before the audio exchange begins. If a hub is found,
its full WebSocket URL (including port) is stored and used in place of the
bare IP from `HMHOST:`. Falls back to plain `GGWaveSlave` behaviour if
`hivemind-presence` is not installed or no hub is found within
`presence_timeout` seconds.

- **Source**: `GGWavePresenceSlave` — `hivemind_ggwave/__init__.py`
