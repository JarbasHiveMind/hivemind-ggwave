# Maintenance Report — hivemind-ggwave

## 2026-03-17
- **AI Model**: Claude Sonnet 4.6
- **Actions Taken**:
  - Refactored `GGWaveMaster.__init__`: made `add_client_callback` a required positional argument; removed optional `hivemind_core` fallback import
  - Replaced `sounddevice` direct import with OVOS microphone plugin interface (`OVOSMicrophoneFactory`); added `_create_microphone()` factory method to `GGWave`
  - Added `microphone: Optional[Microphone]` parameter to `GGWave.__init__` for injecting a pre-constructed plugin instance
  - Added `HMWSP:`, `HMHTTP:`, `HMHOST:` opcodes to `GGWaveMaster` (master emits full WebSocket/HTTP URLs alongside legacy bare IP)
  - Added `handle_wsp()`, `handle_http()`, `handle_host()` handlers to `GGWaveSlave`; priority logic prefers WebSocket URL
  - Added `GGWavePresenceSlave` subclass using `hivemind_presence.LocalDiscovery` for UPnP/Zeroconf hub discovery
  - Rewrote test suite: stubbed `ggwave` via `sys.modules`, removed `sounddevice` stub, fixed duplicate `pswd` kwarg; 30 passing, 9 skipped (binary absent)
  - Migrated `pyproject.toml` to dynamic versioning via `hivemind_ggwave.version.__version__`; pinned dep ranges; added `alsa` and `pyaudio` optional extras
  - Added `__version__` string to `version.py`
  - Added `.github/workflows/coverage.yml` using `OpenVoiceOS/gh-automations@dev`
  - Updated `QUICK_FACTS.md`, `FAQ.md`, `AUDIT.md`, `SUGGESTIONS.md`, `MAINTENANCE_REPORT.md`
- **Oversight**: Human-reviewed; tests verified locally (30/30 pass, 9 skipped)

## 2026-03-08
- **AI Model**: Claude Sonnet 4.6
- **Actions Taken**:
  - Initial compliance with AGENTS.md documentation standards
  - Created `QUICK_FACTS.md`, `FAQ.md`, `MAINTENANCE_REPORT.md`
  - Verified existence of `docs/index.md`
- **Oversight**: Human-reviewed
