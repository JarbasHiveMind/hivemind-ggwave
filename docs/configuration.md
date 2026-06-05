# Configuration

## GGWave transmission

Audio transmission parameters are passed to the `GGWave` transceiver via a
`config` dict:

| Key | Default | Description |
| --- | --- | --- |
| `protocol_id` | `1` | GGWave transmission protocol id (trades speed for robustness). |
| `volume` | `50` | Transmit volume, 0–100. |
| `sample_rate` | `48000` | Audio sample rate in Hz. |

The same `config` dict is forwarded by `GGWaveMaster` and `GGWaveSlave` to the
underlying transceiver, so transmission settings are shared across roles.

## Master

| Parameter | Description |
| --- | --- |
| pairing password | The code shown/broadcast as `HMPSWD:`. Generated if not supplied. |
| host | The hub address emitted as `HMHOST:`. Auto-detected from the local IP if not supplied. |
| silent mode | When enabled, the password is not auto-broadcast; the caller emits it on demand. |
| client-registration callback | Invoked with the access key + password so the caller can persist the new client. |

## Slave

| Parameter | Description |
| --- | --- |
| access key | The key sent back as `HMKEY:`. Generated if not supplied. |

On receiving `HMHOST:`, the slave normalises the host to a WebSocket URL and saves
it as the default master in its `NodeIdentity`.

## Audio capture

GGWave needs raw audio at the configured sample rate. Capture/playback details and
microphone requirements are covered in [microphone.md](microphone.md).
