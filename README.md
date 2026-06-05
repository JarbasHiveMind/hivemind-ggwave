# HiveMind GGWave

Zero-configuration satellite enrollment for [HiveMind](https://github.com/JarbasHiveMind/HiveMind-core)
via **data-over-sound**. Devices pair by playing and listening to short audio
tones ("audio QR codes") using the [GGWave](https://github.com/ggerganov/ggwave)
protocol — no typing IP addresses, scanning QR codes, or sharing a keyboard.

It defines the HiveMind pairing opcodes and provides the master/slave primitives.
Orchestration — when to start, how to show the code, how to register a client — is
the caller's job (typically [hivemind-core](https://github.com/JarbasHiveMind/HiveMind-core)
on the hub).

## Where it sits

A new satellite has no credentials and does not know the hub's address.
HiveMind GGWave bootstraps that first contact over sound:

1. The hub (running `hivemind-core`) shows a pairing **password**.
2. The password is transmitted as audio — emitted by the hub's speaker, or from
   the browser tool at <https://jarbashivemind.github.io/hivemind-ggwave>.
3. The satellite hears it, generates an **access key**, and sends it back over
   sound.
4. The hub registers the satellite as a client and emits its **host address**.
5. The satellite saves the credentials and connects to the hub over the normal
   encrypted HiveMind link.

After enrollment, GGWave is no longer involved — it only establishes the initial
trust.

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
        │  HMHOST:<ip>                     │
        │─────────────────────────────────▶│  (audio)
        │                                  │
        │                    saves identity, connects
```

## Prerequisites

- Python 3.10+
- The `ggwave` audio codec (see [Installation](#installation)).
- Devices within audible range of each other, each with a microphone and speaker.
  The browser tool can stand in for a hub speaker, or for a satellite when pairing
  from a phone.

## Installation

```bash
pip install hivemind-ggwave
```

From source:

```bash
git clone https://github.com/JarbasHiveMind/hivemind-ggwave
cd hivemind-ggwave
pip install -e .
```

GGWave audio I/O is provided by the `ggwave` package and the system audio stack;
see [`docs/microphone.md`](docs/microphone.md) for audio capture details.

## Quickstart

The smallest path is pairing one satellite to a running hub.

1. **Start the hub.** `hivemind-core` runs `GGWaveMaster` and prints a pairing
   code, e.g. `HMPSWD:ce357a6b59f6b1f9`.

2. **Emit the password.** Either let the hub broadcast it from its speaker, or
   open <https://jarbashivemind.github.io/hivemind-ggwave> on a phone, enter the
   code, and play it.

3. **Let the satellite pair.** The unpaired satellite (running `GGWaveSlave`)
   decodes the password, generates an access key, sends it back over sound, and
   receives the hub address.

4. **Done.** The satellite saves its `NodeIdentity` and connects to the hub.

### Silent mode

By default the master broadcasts the password periodically. In `silent_mode` it
does not — the caller shows the code in a UI and triggers transmission on user
demand (e.g. a button press), so the password is emitted once instead of looping.
This is the recommended production flow and the one `hivemind-core` uses.

## Configuration

GGWave transmission parameters are passed via a `config` dict (TX volume, GGWave
protocol id, sample rate). The master accepts the pairing password, hub host, and
the silent-mode flag. See [`docs/configuration.md`](docs/configuration.md) for the
full reference.

## Documentation

See [`docs/`](docs/index.md):

- [Pairing protocol](docs/protocol.md) — the opcodes and handshake.
- [Master and slave](docs/master_slave.md) — the enrollment primitives.
- [Configuration](docs/configuration.md) — parameters and silent mode.
- [Microphone / audio](docs/microphone.md) — audio capture requirements.

## License

Apache-2.0
