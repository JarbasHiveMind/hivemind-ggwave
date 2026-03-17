
# Quick Facts — hivemind-ggwave

Audio QR code pairing (data-over-sound) for HiveMind.

## Package Details
- **Package Name**: `hivemind_ggwave`
- **Version**: `0.0.2`
- **Role**: Audio-based pairing and discovery using the GGWave protocol.

## Key Classes
- `GGWave`: Base thread for sending and receiving GGWave audio payloads.
- `GGWaveMaster`: Server-side implementation (runs on `hivemind-core`) that broadcasts passwords and registers clients.
- `GGWaveSlave`: Client-side implementation (runs on satellites) that listens for passwords and sends access keys.
- `GGWavePresenceSlave`: Extended slave that attempts to discover the hub via `hivemind-presence` (UPnP/Zeroconf) before falling back to bare IP.

## Opcodes
- `HMPSWD:`: Password broadcast from Master.
- `HMKEY:`: Access key response from Slave.
- `HMHOST:`: Host IP broadcast from Master (legacy).
- `HMWSP:`: WebSocket URL broadcast from Master.
- `HMHTTP:`: HTTP URL broadcast from Master.
