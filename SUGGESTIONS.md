# hivemind-ggwave — Suggestions

## HMAC/TOTP Authentication for Pairing Exchange
- **Problem**: The password is transmitted in plaintext over audio. Any device in proximity can intercept both `HMPSWD:` and `HMKEY:` opcodes.
- **Proposed Solution**: Add a time-based challenge-response step — master emits a nonce alongside the password; satellite signs it with a shared secret before transmitting the key. Prevents replay attacks and eavesdropping.
- **Estimated Impact**: Significantly raises the bar for proximity attacks.

## Pairing Timeout on Slave
- **Problem**: `GGWaveSlave` runs indefinitely if the master never sends `HMHOST:/HMWSP:/HMHTTP:` (RF interference, master crash, etc.).
- **Proposed Solution**: Add a configurable `pairing_timeout` (default 120 s) to `GGWaveSlave.__init__`. If no identity is saved within the window, call `stop()` and emit `hm.ggwave.timeout` on the bus.
- **Estimated Impact**: Prevents satellites from hanging in pairing mode permanently.
- **Citation**: `hivemind_ggwave/__init__.py:340-352`

## Duplicate Key Detection in Master
- **Problem**: If a satellite resets and re-pairs, `add_client_callback` is called again, potentially creating a duplicate database entry.
- **Proposed Solution**: `GGWaveMaster.add_client()` should include a `duplicate: bool` field in the `hm.ggwave.client_registered` event so the hub can upsert rather than insert.
- **Estimated Impact**: Eliminates stale credential accumulation on satellite reset.
- **Citation**: `hivemind_ggwave/__init__.py:260-266`

## Pairing Success Audio Confirmation on Slave
- **Problem**: Satellite has no audio cue when `_save_identity()` succeeds; users rely on logs.
- **Proposed Solution**: After `_save_identity()` succeeds, emit a short confirmation tone (e.g., `self.ggwave.emit("HMDONE:")`).
- **Estimated Impact**: Clearer UX without requiring a display.
- **Citation**: `hivemind_ggwave/__init__.py:390-415`

## Auto-Stop Master After First Client
- **Problem**: `GGWaveMaster` continues broadcasting after a client registers, consuming audio resources and potentially accepting unintended pairings.
- **Proposed Solution**: Add `auto_stop: bool = False` to `GGWaveMaster`. When `True`, call `stop()` inside `add_client()` after the callback fires.
- **Estimated Impact**: Reduces resource use; prevents accidental double-pairing.
- **Citation**: `hivemind_ggwave/__init__.py:270-284`

## Volume Optimization for Pairing
- **Problem**: GGWave signal volume may be too low or too high depending on hardware.
- **Proposed Solution**: Expose `volume` as a documented user-facing config key (range 0–100, default 50). Log the RMS amplitude of the encoded WAV before playback; warn if below a configurable threshold.
- **Estimated Impact**: Increased pairing success rate across hardware configurations.
