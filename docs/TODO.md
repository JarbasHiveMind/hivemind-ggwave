# TODO — hivemind-ggwave

## Known issues

- **No authentication of the pairing exchange** — the satellite simply waits to receive a password, generates a key, and sends it. Any device in range listening on the ggwave frequency can intercept the password (it is broadcast in the clear as audio). The pairing is trivially sniffable in proximity.

## Missing features

- **No duplicate key handling** — if the same satellite runs GGWave twice (e.g. after a reset), `add_client()` adds a second entry rather than updating the existing one, creating duplicate entries in the database.
- **No timeout for slave pairing** — `GGWaveSlave` runs indefinitely until `handle_host()` calls `stop()`. If the master never sends `HMHOST:` (e.g. due to RF interference), the slave never exits pairing mode.
- **No pairing confirmation sound on the satellite** — after `handle_host()` saves the identity, there is no local audio cue to confirm successful pairing.
- **`GGWaveMaster` does not stop broadcasting after first pairing** — the password broadcast loop continues even after a client has been registered. Ideally the master should stop or pause after a successful pairing.
- **Silent mode UX is unclear** — in `silent_mode`, the password is logged but not displayed in any UI. The user has to read logs to find the code.

## Resolved

- ~~**`GGWaveMaster` adds clients to `hivemind-core` directly**~~ — `add_client_callback`
  parameter added to `GGWaveMaster`. When set, the callback is called instead of
  importing `hivemind_core.ClientDatabase`. The default (no callback) preserves
  backward compatibility.

## Architecture suggestions

- ~~Split the `add_client()` logic out of `GGWaveMaster` and into a callback~~ — done (see above)
- ~~Use the `ggwave` Python bindings instead of subprocess `pexpect`~~ — done; `GGWave` now uses `ggwave` + `sounddevice` directly
- Add a TOTP or HMAC-based authentication step to the pairing protocol to prevent passive eavesdropping attacks
- Add a pairing timeout to `GGWaveSlave` (e.g. 2 minutes) after which it gives up and emits a `hm.ggwave.pairing_failed` event

## Testing gaps

- ~~No tests for the opcode dispatch logic in `GGWave.run()`~~ — covered in `TestGGWaveOpcodeLogic`
- ~~No test for `GGWaveMaster.add_client()`~~ — `TestGGWaveMasterCallback` covers the callback path without requiring a real database
- No test for `GGWaveSlave.handle_host()` identity saving (requires audio hardware)
