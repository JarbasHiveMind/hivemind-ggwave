# Microphone / audio

GGWave is a data-over-sound codec: pairing payloads are transmitted by playing
audio through a speaker and received by capturing audio from a microphone. Both
the hub and the satellite therefore need working audio I/O, and the two devices
must be within audible range.

## Requirements

- A speaker to emit `HMPSWD:` / `HMKEY:` / `HMHOST:` tones.
- A microphone to decode the tones sent by the other device.
- Audio captured at the GGWave sample rate (default 48 kHz).

## Capture

The receive loop reads audio chunks and feeds them to the GGWave decoder; when a
complete payload is recognised, the matching opcode handler runs. Transmit encodes
the payload to PCM and plays it back through the system audio output.

## Tips

- Keep devices close and the environment reasonably quiet; GGWave is robust but
  not immune to loud background noise.
- If the hub has no speaker (or you prefer to pair from a phone), use the browser
  tool at <https://jarbashivemind.github.io/hivemind-ggwave> to emit/decode the
  same tones.
- Volume that is too low fails to decode; too high can clip. Tune `volume` in the
  GGWave `config` if pairing is unreliable.
