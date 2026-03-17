# Microphone Plugin Configuration

`GGWave` captures audio via the
[OVOS microphone plugin system](https://github.com/OpenVoiceOS/ovos-plugin-manager).
Any plugin that produces **float32 mono audio** at the configured sample rate
can be used.

---

## Float32 requirement

`ggwave.decode()` expects raw **float32** PCM samples.  The plugin must be
configured with `sample_width=4` **and** must actually produce IEEE 754
float32 bytes — not signed 32-bit integer (S32_LE).

| Plugin | float32 support | Notes |
|---|---|---|
| `ovos-microphone-plugin-sounddevice` | ✅ | Maps `sample_width=4` to `dtype=float32` |
| `ovos-microphone-plugin-files` | ✅ | Reads `.wav` files; file must be float32 |
| `ovos-microphone-plugin-alsa` | ❌ | `sample_width=4` → `PCM_FORMAT_S32_LE` (int32) |
| `ovos-microphone-plugin-pyaudio` | ❌ | `sample_width=4` → PyAudio int32 format |

ALSA and PyAudio require an int32→float32 conversion wrapper before use with
ggwave.  The recommended approach is to pass a custom `Microphone` instance
(see [Custom microphone](#custom-microphone-instance) below).

---

## Default behaviour

If no `microphone` key is present in `config` and no `microphone=` argument is
passed, `GGWave` calls `OVOSMicrophoneFactory.create()` with no arguments,
which reads the system OVOS listener config
(`~/.config/mycroft/mycroft.conf` → `listener.microphone`).

That factory-created instance receives `sample_rate`, `sample_width=4`,
`sample_channels=1`, and `chunk_size` overrides only when a `module` key is
also present in `config["microphone"]`.  If you rely on the system config,
ensure the configured plugin produces float32 output.

---

## Plugin config examples

All examples assume `GGWave` is constructed with the shown `config` dict.
`sample_rate`, `sample_width`, `sample_channels`, and `chunk_size` are
injected automatically when a `module` key is present — you do not need to
repeat them unless you want to override the defaults.

### sounddevice (recommended, cross-platform)

```python
# pip install "hivemind-ggwave[sounddevice]"
config = {
    "microphone": {
        "module": "ovos-microphone-plugin-sounddevice",
        "ovos-microphone-plugin-sounddevice": {
            "device": "default",  # device name, index, or None for system default
            "latency": "low",
        },
    }
}
ggwave = GGWave(config=config)
```

### files (testing / CI)

Reads `.wav` files dropped into a directory.  Files must be float32 mono at
`sample_rate` Hz (default 48 000 Hz).

```python
# pip install ovos-microphone-plugin-files
config = {
    "microphone": {
        "module": "ovos-microphone-plugin-files",
        "ovos-microphone-plugin-files": {
            "files_folder": "/tmp/ggwave-input",
            "autodelete": True,
        },
    }
}
ggwave = GGWave(config=config)
```

---

## Custom microphone instance

Pass a pre-constructed `Microphone` to skip the factory entirely.  This is
the recommended path for ALSA/PyAudio users and for unit tests.

```python
from ovos_plugin_manager.templates.microphone import Microphone

class MyMicrophone(Microphone):
    sample_rate: int = 48_000
    sample_width: int = 4        # float32
    sample_channels: int = 1
    chunk_size: int = 4096       # block_size * sample_width

    def start(self) -> None: ...
    def read_chunk(self) -> Optional[bytes]: ...
    def stop(self) -> None: ...

ggwave = GGWave(microphone=MyMicrophone())
```

### ALSA with int32→float32 conversion

ALSA captures S32_LE (big-endian signed 32-bit integer) when
`sample_width=4`.  The wrapper below converts each chunk before handing it
to ggwave.

```python
import struct
from ovos_microphone_plugin_alsa import AlsaMicrophone

class AlsaFloat32Microphone(AlsaMicrophone):
    """Wraps AlsaMicrophone and converts S32_LE → float32."""

    sample_rate: int = 48_000
    sample_width: int = 4
    sample_channels: int = 1
    chunk_size: int = 4096  # bytes (= 1024 float32 frames)

    def read_chunk(self) -> Optional[bytes]:
        raw = super().read_chunk()
        if raw is None:
            return None
        # S32_LE → float32: divide each signed 32-bit sample by 2**31
        n = len(raw) // 4
        samples = struct.unpack(f"<{n}i", raw)
        return struct.pack(f"{n}f", *(s / 2_147_483_648.0 for s in samples))

ggwave = GGWave(microphone=AlsaFloat32Microphone())
```

### PyAudio with int32→float32 conversion

PyAudio similarly returns int32 for `sample_width=4`.  Apply the same
conversion pattern as the ALSA example above, subclassing
`PyAudioMicrophone` and overriding `read_chunk()`.
