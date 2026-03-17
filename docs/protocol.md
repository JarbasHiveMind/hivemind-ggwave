# GGWave Protocol and Opcodes

HiveMind GGWave defines a set of simple opcodes to manage the audio-based enrollment process. These are handled in the `GGWave.run()` loop by parsing incoming text from `ggwave-rx`.

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
Spawns the `ggwave-rx` process using `pexpect` and listens for the "Received sound data successfully" marker. It then extracts the opcode and calls the appropriate handler.
- **Source**: `GGWave.run()`

### 2. `emit(payload)`
Sends a payload by either spawning `ggwave-cli` or generating a WAV file via the `encode2wave()` method and playing it.
- **Source**: `GGWave.emit(payload)`

### 3. `encode2wave(message, wav_path)`
Encodes a text message into an audio WAV file using the `ggwave-to-file` web service (fallback implementation).
- **Source**: `GGWave.encode2wave(message, wav_path)`
