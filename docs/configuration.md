# Configuration

## GGWave transceiver

The `GGWave` class is configured via a `config` dict:

| Key | Default | Description |
| --- | --- | --- |
| `ggwave-rx` | path of `ggwave-rx` on `$PATH`, else `~/.local/bin/ggwave-rx` | Path to the `ggwave-rx` binary used to listen for incoming audio. |
| `ggwave-cli` | path of `ggwave-cli` on `$PATH`, else `~/.local/bin/ggwave-cli` | Path to the `ggwave-cli` binary used to emit audio locally. |
| `remote` | `False` (forced to `True` if `ggwave-cli` is not found) | When set, audio is generated via the `ggwave-to-file` web service and played back instead of using the local `ggwave-cli` binary. |

The same `config` dict is forwarded by `GGWaveMaster` and `GGWaveSlave` to the
underlying transceiver, so these settings are shared across roles. The GGWave
protocol id, transmit volume, and sample rate used when generating audio
remotely are fixed in code, not configurable.

## Master

| Parameter | Description |
| --- | --- |
| pairing password | The code shown/broadcast as `HMPSWD:`. Generated if not supplied. |
| host | The hub address emitted as `HMHOST:`. Auto-detected from the local IP if not supplied. |
| silent mode | When enabled, the password is not auto-broadcast; the caller emits it on demand. |

## Slave

| Parameter | Description |
| --- | --- |
| access key | The key sent back as `HMKEY:`. Generated if not supplied. |

On receiving `HMHOST:`, the slave normalises the host to a WebSocket URL and saves
it as the default master in its `NodeIdentity`.

## Audio capture

GGWave needs raw audio at the configured sample rate. Capture/playback details and
microphone requirements are covered in [microphone.md](microphone.md).
