# GGWave Protocol and Opcodes

HiveMind GGWave defines a set of simple opcodes to manage the audio-based enrollment process. These are handled in the `GGWave.run()` loop by decoding audio via the `ggwave` Python bindings.

- **Source File**: `hivemind-ggwave/hivemind_ggwave/__init__.py`
- **Primary Class**: `GGWave(threading.Thread)`

## Custom Opcodes

The `GGWave` class uses a dictionary `self.OPCODES` to map incoming sound data to handler methods.

| Opcode | Payload | Sent By | Description |
|---|---|---|---|
| **`HMPSWD:`** | Password | Master | Broadcasts the temporary password for enrollment. |
| **`HMKEY:`** | Access Key | Slave | Sends the newly generated access key to the Master. |
| **`HMWSP:`** | WS URL | Master | Provides the full WebSocket URL (with port and SSL info). |
| **`HMHTTP:`** | HTTP URL | Master | Provides the full HTTP URL (as a fallback). |
| **`HMHOST:`** | Host IP | Master | Provides the bare IP address (for backward compatibility). |

## Core Methods

### 1. `run()`
Captures audio via `sounddevice.RawInputStream`, feeds each block to `ggwave.decode()`, and dispatches recognised payloads to the matching opcode handler.
- **Source**: `GGWave.run()` — `hivemind_ggwave/__init__.py`

### 2. `emit(payload)`
Encodes *payload* with `ggwave.encode()`, wraps the float32 PCM samples in a WAV container, and plays it via `ovos_utils.sound.play_audio`.
- **Source**: `GGWave.emit(payload)` — `hivemind_ggwave/__init__.py`
