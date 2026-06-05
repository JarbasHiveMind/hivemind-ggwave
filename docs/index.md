# HiveMind GGWave

Zero-configuration satellite enrollment for HiveMind via data-over-sound. Devices
pair by playing and listening to GGWave audio tones — an "audio QR code" — so a
fresh satellite can join a hub without typed credentials or a hub address.

- [Pairing protocol](protocol.md)
- [Master and slave](master_slave.md)
- [Configuration](configuration.md)
- [Microphone / audio](microphone.md)

## Where it sits

HiveMind GGWave is the enrollment bootstrap for the
[HiveMind](https://github.com/JarbasHiveMind/HiveMind-core) mesh. It carries only
the first-contact exchange (password → access key → host); once the satellite has
credentials and the hub address it connects over the normal encrypted HiveMind
link and GGWave drops out.

The library ships **primitives** — the pairing opcodes and the `GGWaveMaster` /
`GGWaveSlave` classes. Deciding when to start, how to present the code, and how to
persist a registered client is the caller's responsibility (e.g. `hivemind-core`).

## Browser tool

The page at <https://jarbashivemind.github.io/hivemind-ggwave> can emit and decode
the same tones from any device with a speaker/microphone — useful when the hub has
no speaker, or to pair from a phone.
