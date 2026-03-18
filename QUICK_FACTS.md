# Quick Facts — hivemind-ggwave

Audio pairing (data-over-sound) for HiveMind using the GGWave protocol.

## Package Details
- **Package Name**: `hivemind_ggwave`
- **Version**: `0.0.2` (`hivemind_ggwave/version.py`)
- **Entry Point**: none (library only — instantiate classes directly)
- **Python**: ≥3.10 (3.13 blocked by upstream `ggwave` C extension)

## Key Classes (`hivemind_ggwave/__init__.py`)

| Class | Role | Key Parameters |
|---|---|---|
| `GGWave` | Base audio transceiver thread | `config`, `callbacks`, `microphone` |
| `GGWaveMaster` | Hub-side orchestrator | `add_client_callback` (required), `pswd`, `host`, `ws_port`, `http_port`, `silent_mode` |
| `GGWaveSlave` | Satellite-side orchestrator | `key`, `bus`, `config` |
| `GGWavePresenceSlave` | Slave with UPnP/Zeroconf discovery | `presence_timeout` (default 25 s) |

## Opcodes

| Opcode | Direction | Payload |
|---|---|---|
| `HMPSWD:` | Master → Satellite | Pairing password |
| `HMKEY:` | Satellite → Master | Generated access key |
| `HMWSP:` | Master → Satellite | Full WebSocket URL (`ws://` or `wss://`) |
| `HMHTTP:` | Master → Satellite | Full HTTP URL (`http://` or `https://`) |
| `HMHOST:` | Master → Satellite | Bare IP address (legacy fallback) |

## Audio Constants
- Sample rate: 48000 Hz
- Channels: 1 (mono)
- Block size: 1024 frames
- Sample width: 4 bytes (float32)

## Bus Events Emitted

| Event | Emitter | Data |
|---|---|---|
| `hm.ggwave.activated` | Master / Slave | — |
| `hm.ggwave.deactivated` | Master / Slave | — |
| `hm.ggwave.client_registered` | Master | `{key, pswd}` |

## Optional Extras
```
pip install "hivemind-ggwave[sounddevice]"   # sounddevice mic plugin
pip install "hivemind-ggwave[alsa]"          # ALSA mic plugin
pip install "hivemind-ggwave[pyaudio]"       # PyAudio mic plugin
```
