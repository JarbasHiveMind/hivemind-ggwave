# FAQ — hivemind-ggwave

## What is GGWave?
GGWave is a tiny data-over-sound library. `hivemind-ggwave` uses it to allow "audio pairing" between a HiveMind hub and a new satellite — no network required for initial setup.

## How do I use audio pairing?
1. The hub (`GGWaveMaster`) starts and chirps the password over the speaker.
2. The satellite (`GGWaveSlave`) starts, listens for the password, then chirps back an access key.
3. The hub receives the key, calls `add_client_callback(key, pswd)`, and chirps the connection URL.
4. The satellite receives the URL, saves the identity to `NodeIdentity`, and stops.

## What microphone/speaker hardware is required?
Any microphone and speaker accessible to the OS. The default OVOS microphone plugin is used unless overridden via `config["microphone"]`. For ggwave compatibility the microphone **must** be configured with `float32_output: true`. See `docs/microphone.md` for per-plugin setup.

## Which microphone plugins support float32?
All four OVOS microphone plugins support it:

| Plugin | `float32_output` mechanism |
|---|---|
| `ovos-microphone-plugin-sounddevice` | `dtype="float32"` |
| `ovos-microphone-plugin-alsa` | `PCM_FORMAT_FLOAT_LE` |
| `ovos-microphone-plugin-pyaudio` | `pyaudio.paFloat32` |
| `ovos-microphone-plugin-files` | `AudioData.get_np_float32()` |

## Is it secure?
The password is transmitted in plaintext over audio and can be overheard by anyone in range. It is intended for convenient initial pairing in a controlled environment. Once paired, standard HiveMind encryption (AES-256) is used for the network connection.

## Can I pair multiple satellites at once?
Not simultaneously — `GGWaveMaster` broadcasts one password and registers the first key it receives. Run separate pairing sessions for each satellite.

## What happens if the satellite resets after pairing?
It will re-pair and call `add_client_callback` again. The hub may create a duplicate entry. Until duplicate detection is implemented (see `SUGGESTIONS.md`), the old entry should be removed manually from the hub database before re-pairing.

## What happens if the master never finishes the handshake?
`GGWaveSlave` will run until `stop()` is called manually. There is currently no built-in timeout — see `SUGGESTIONS.md` for the proposed fix.

## How do I control the broadcast volume?
Pass `config={"volume": 50}` to `GGWaveMaster` or `GGWaveSlave`. Volume is 0–100; default is 50.

## Why is `ggwave` not importable on Python 3.13?
The `ggwave` C extension uses a removed CPython internal (`ob_digit`). Until the upstream package is updated, use Python 3.10–3.12.

## How do I run the tests without audio hardware?
All unit tests stub out the `ggwave` C extension via `sys.modules`. Run:
```bash
uv run pytest test/ -v
```
9 integration tests that invoke the real `ggwave-rx` binary are automatically skipped when the binary is not installed.
