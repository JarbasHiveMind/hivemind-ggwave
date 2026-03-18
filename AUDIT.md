# HiveMind GGWave — Audit Report

## Test Status
- **Status**: ⚠️ Partial Pass (77% coverage)
- **Command**: `uv run pytest test/ -v`
- **Results** (2026-03-17):
  - **Passed**: 30 tests
  - **Skipped**: 9 tests (integration tests requiring `ggwave-rx` binary)
  - **Failures**: 0

## Known Issues

### 1. No Authentication in Pairing Exchange
- **Severity**: High
- **Issue**: `HMPSWD:` and `HMKEY:` are transmitted in plaintext over audio. Any device within range can intercept both values.
- **Citation**: `hivemind_ggwave/__init__.py:167-176`

### 2. No Pairing Timeout on Slave
- **Severity**: Medium
- **Issue**: `GGWaveSlave` runs indefinitely if the master never completes the handshake. No escape mechanism.
- **Citation**: `hivemind_ggwave/__init__.py:340-352`

### 3. No Duplicate Key Detection
- **Severity**: Medium
- **Issue**: If a satellite re-pairs after reset, `add_client_callback` is invoked again without signalling that the key already exists. Creates duplicate entries in the hub database.
- **Citation**: `hivemind_ggwave/__init__.py:260-266`

### 4. Continuous Broadcasting After Client Registered
- **Severity**: Medium
- **Issue**: `GGWaveMaster` keeps broadcasting even after a client successfully registers. Caller must manually call `stop()`.
- **Citation**: `hivemind_ggwave/__init__.py:270-284`

### 5. Dependency on External Binaries
- **Severity**: Medium
- **Issue**: 9 integration tests require `ggwave-rx` or `ggwave-cli` binaries installed on the test host. Cannot run in standard CI without them.
- **Evidence**: `test/test_ggwave.py` — `skipIf` guards on binary presence.

### 6. `distutils` Deprecation
- **Severity**: Low (currently suppressed by ovos_utils)
- **Issue**: `distutils.spawn.find_executable` (used transitively via `ovos_utils.sound`) is removed in Python 3.12+. Produces 50+ `DeprecationWarning` messages in test output.
- **Action**: Resolved upstream in `ovos_utils` when migrated to `shutil.which`.

### 7. No Input Validation on Opcode Payloads
- **Severity**: Low
- **Issue**: Payloads decoded from audio are passed directly to handlers and `NodeIdentity` without sanitisation. A crafted acoustic signal could inject unexpected data.
- **Citation**: `hivemind_ggwave/__init__.py:167-176`

## Documentation Status
- [x] `QUICK_FACTS.md`
- [x] `FAQ.md`
- [x] `MAINTENANCE_REPORT.md`
- [x] `AUDIT.md`
- [x] `SUGGESTIONS.md`
- [x] `docs/index.md`
- [x] `docs/api.md`
- [x] `docs/protocol.md`
- [x] `docs/master_slave.md`
- [x] `docs/microphone.md`
- [x] `docs/TODO.md`
