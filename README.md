# HiveMind GGWave

Zero-configuration satellite enrollment for HiveMind via data-over-sound.

This library defines the **GGWave pairing protocol opcodes** and provides the
primitive classes (`GGWave`, `GGWaveMaster`, `GGWaveSlave`) that implement
them. Orchestration — when to start/stop, how to display the pairing code,
how to register clients — is the responsibility of the **caller** (e.g.
`hivemind-core`).

## How it works

```
Hub (GGWaveMaster)               Satellite (GGWaveSlave)
        │                                  │
        │  HMPSWD:<password>               │
        │─────────────────────────────────▶│  (audio)
        │                                  │
        │                   HMKEY:<key>    │
        │◀─────────────────────────────────│  (audio)
        │                                  │
        │  [optional] HMWSP:<ws://ip:port> │
        │─────────────────────────────────▶│
        │  [optional] HMHTTP:<http://...>  │
        │─────────────────────────────────▶│
        │  HMHOST:<ip>  (backward compat)  │
        │─────────────────────────────────▶│
        │                                  │
        │                    saves identity, connects
```

## Silent mode

When `silent_mode=True`, `GGWaveMaster` does **not** broadcast the password
automatically. The caller is responsible for showing the code in a UI and
triggering the transmission at the right moment.

For example, `hivemind-core` will display the code on screen and wait for the
user to press a button before emitting it. This is safer than the default
broadcast loop — the password is only transmitted once, on user demand.

```python
master = GGWaveMaster(silent_mode=True, add_client_callback=my_register_fn)
master.start()
# master.pswd is set once run() initialises. Caller emits when ready:
master.ggwave.emit(f"HMPSWD:{master.pswd}")
```

Alternatively, the code can be entered manually at
https://jarbashivemind.github.io/hivemind-ggwave — useful when the hub has no
speaker, or when the user wants to pair from a phone.

## Installation

```bash
pip install hivemind-ggwave
```

Requires the `ggwave` Python package and `sounddevice`.
