# Master and Slave Implementations

The `GGWaveMaster` and `GGWaveSlave` classes implement the high-level enrollment logic.

- **Source File**: `hivemind-ggwave/hivemind_ggwave/__init__.py`
- **Primary Classes**: `GGWaveMaster` and `GGWaveSlave`

## 1. `GGWaveMaster` (Runs on the Mind)

Manages password broadcasting and client registration.
- **`run()`**: Periodically emits the `HMPSWD:` opcode with a generated password (using `os.urandom(8).hex()`).
- **`handle_key(payload)`**: Triggered when an `HMKEY:` opcode is received. It calls `self.add_client(payload)` and then broadcasts the Mind's connection URLs (`HMWSP:` or `HMHOST:`).
- **`add_client(access_key)`**: Registers the new client in the HiveMind database (`hivemind_core.database.ClientDatabase`) using the broadcasted password.

## 2. `GGWaveSlave` (Runs on the Satellite)

Listens for the Mind's broadcast and transmits its enrollment request.
- **`handle_pswd(payload)`**: Triggered when an `HMPSWD:` opcode is received. It stores the password and transmits its new access key via the `HMKEY:` opcode.
- **`handle_wsp(payload)`**: Triggered when the Mind sends its connection URL.
- **`_save_identity(host)`**: Once both the password and host are received, it persists them using `hivemind_bus_client.identity.NodeIdentity`.

## Presence Integration
The `GGWavePresenceSlave` class extends the basic slave by adding local discovery via `hivemind-presence`. It attempts to find the Mind's URL via UPnP/Zeroconf *before* falling back to the GGWave-provided IP.
- **Source**: `hivemind_ggwave.__init__.GGWavePresenceSlave`
