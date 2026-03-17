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

All four plugins now support `float32_output: bool = False`.  Set it to
``True`` to enable float32 output:

| Plugin | `float32_output=True` mechanism |
|---|---|
| `ovos-microphone-plugin-sounddevice` | Uses `dtype="float32"` in `sd.RawInputStream`; gain/downmix work natively |
| `ovos-microphone-plugin-alsa` | Opens `PCM_FORMAT_FLOAT_LE` ALSA format |
| `ovos-microphone-plugin-pyaudio` | Uses `pyaudio.paFloat32`; bypasses speech_recognition abstraction |
| `ovos-microphone-plugin-files` | Converts via `AudioData.get_np_float32()` (normalised −1.0…+1.0) |

> **Note for sounddevice**: float32 resampling is not implemented.  If the
> device's native sample rate differs from `sample_rate`, configure
> `sample_rate` to match the device rather than relying on software
> resampling.

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
            "float32_output": True,
        },
    }
}
ggwave = GGWave(config=config)
```

### ALSA (Linux)

```python
# pip install ovos-microphone-plugin-alsa
config = {
    "microphone": {
        "module": "ovos-microphone-plugin-alsa",
        "ovos-microphone-plugin-alsa": {
            "device": "default",
            "float32_output": True,
        },
    }
}
ggwave = GGWave(config=config)
```

### PyAudio (cross-platform)

```python
# pip install ovos-microphone-plugin-pyaudio
config = {
    "microphone": {
        "module": "ovos-microphone-plugin-pyaudio",
        "ovos-microphone-plugin-pyaudio": {
            "device": "default",
            "float32_output": True,
        },
    }
}
ggwave = GGWave(config=config)
```

### files (testing / CI)

Reads audio files dropped into a directory.  Set `float32_output=True` so
the plugin converts the file's PCM data to float32 before queuing.

```python
# pip install ovos-microphone-plugin-files
config = {
    "microphone": {
        "module": "ovos-microphone-plugin-files",
        "ovos-microphone-plugin-files": {
            "files_folder": "/tmp/ggwave-input",
            "autodelete": True,
            "float32_output": True,
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

