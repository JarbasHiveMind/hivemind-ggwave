
# HiveMind GGWave

HiveMind GGWave provides an "audio QR code" transport for zero-configuration enrollment of new satellites. It uses the `ggwave` library to transmit credentials and connection info over sound.

## Documentation Guides

- [GGWave Protocol](protocol.md) - The custom opcodes and handshake flow.
- [Master and Slave](master_slave.md) - Implementation of the enrollment process.

## Overview

GGWave allows a Mind to "broadcast" a temporary password over audio. A satellite listening for this signal can then generate its own access key and transmit it back to the Mind, completing the enrollment without any manual configuration or network pre-sharing.

## Installation

```bash
pip install -e hivemind-ggwave/
```
> **Note**: Requires the `ggwave` Python package and `sounddevice`.

## Core Components

- **`GGWave`**: The base thread for sending and receiving audio payloads.
- **`GGWaveMaster`**: Runs on the Mind to broadcast passwords and register clients.
- **`GGWaveSlave`**: Runs on the Satellite to listen for passwords and send access keys.
