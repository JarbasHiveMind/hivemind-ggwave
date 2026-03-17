
# HiveMind GGWave

HiveMind GGWave provides an "audio QR code" transport for zero-configuration enrollment of new satellites. It uses the `ggwave` library to transmit credentials and connection info over sound.

## Documentation Guides

- [GGWave Protocol](protocol.md) - The custom opcodes and handshake flow.
- [Master and Slave](master_slave.md) - Implementation of the enrollment process.
- [Microphone Plugins](microphone.md) - Supported plugins, float32 requirement, config examples.

## Overview

This library provides **primitives** — protocol opcode definitions and the
classes that implement them. The caller (e.g. `hivemind-core`) is responsible
for orchestration: when to start/stop, how to present the pairing code to the
user, and how to register clients.

In **silent mode** the hub does not broadcast the password automatically. The
caller shows the code in a UI and triggers transmission on user demand (e.g. a
button press). This is the recommended production flow. The browser tool at
https://jarbashivemind.github.io/hivemind-ggwave provides the same capability
without a hub speaker.

## Installation

```bash
pip install -e hivemind-ggwave/
```

> **Note**: Requires the `ggwave` Python package.  Audio capture uses the
> OVOS microphone plugin system (`ovos-plugin-manager`).  The default plugin
> is `ovos-microphone-plugin-sounddevice`:
> ```bash
> pip install "hivemind-ggwave[sounddevice]"
> ```
> Any other OVOS-compatible microphone plugin can be used instead — pass a
> pre-constructed `Microphone` instance to `GGWave(microphone=...)` or
> configure `microphone.module` in the `config` dict.

## Core Components

- **`GGWave`**: The base thread for sending and receiving audio payloads.
- **`GGWaveMaster`**: Runs on the Mind to broadcast passwords and register clients.
- **`GGWaveSlave`**: Runs on the Satellite to listen for passwords and send access keys.
