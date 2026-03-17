import builtins
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Stub out native extensions that cannot build in the test environment.
# These must be inserted before any hivemind_ggwave import.
# ---------------------------------------------------------------------------
_ggwave_stub = types.ModuleType("ggwave")
_ggwave_stub.init = MagicMock(return_value=MagicMock())
_ggwave_stub.free = MagicMock()
_ggwave_stub.decode = MagicMock(return_value=None)
_ggwave_stub.encode = MagicMock(return_value=b"\x00" * 16)
sys.modules.setdefault("ggwave", _ggwave_stub)

_sd_stub = types.ModuleType("sounddevice")
_sd_stub.RawInputStream = MagicMock()
sys.modules.setdefault("sounddevice", _sd_stub)


# ---------------------------------------------------------------------------
# Helpers — patch ggwave.init so GGWave() can be constructed in tests
# without audio hardware or the compiled ggwave extension.
# ---------------------------------------------------------------------------

def _ggwave_init_patch():
    """Return a context manager that stubs out ggwave.init/free/decode/encode."""
    return patch.multiple(
        "hivemind_ggwave.ggwave",
        init=MagicMock(return_value=MagicMock()),
        free=MagicMock(),
        decode=MagicMock(return_value=None),
        encode=MagicMock(return_value=b"\x00" * 16),
    )


def _make_slave(cls=None):
    if cls is None:
        from hivemind_ggwave import GGWaveSlave as cls
    with _ggwave_init_patch():
        slave = cls()
    slave.ggwave = MagicMock()
    slave.ggwave.running = True
    slave.bus = MagicMock()
    slave.pswd = "mypw"
    slave.key = "mykey"
    return slave


def _make_master(callback=None, **kwargs):
    from hivemind_ggwave import GGWaveMaster
    cb = callback or MagicMock()
    with _ggwave_init_patch():
        master = GGWaveMaster(cb, pswd="pw", host="192.168.1.1", **kwargs)
    master.ggwave = MagicMock()
    master.ggwave.running = True
    master.bus = MagicMock()
    return master


# ---------------------------------------------------------------------------
# Opcode dispatch logic (no audio hardware needed)
# ---------------------------------------------------------------------------

class TestGGWaveOpcodeLogic(unittest.TestCase):
    """Opcode dispatch logic tested independently of audio I/O."""

    def test_opcode_match(self):
        opcodes = {
            "HMKEY:": MagicMock(),
            "HMPSWD:": MagicMock(),
            "HMWSP:": MagicMock(),
            "HMHTTP:": MagicMock(),
            "HMHOST:": MagicMock(),
        }
        payload = "HMKEY:abc123"
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                handler(payload.split(opcode, 1)[-1])
                break

        opcodes["HMKEY:"].assert_called_once_with("abc123")
        for op in ("HMPSWD:", "HMWSP:", "HMHTTP:", "HMHOST:"):
            opcodes[op].assert_not_called()

    def test_unknown_opcode_does_not_call_handlers(self):
        called = []
        opcodes = {"HMKEY:": lambda p: called.append("HMKEY")}
        payload = "UNKNOWN:payload"
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                handler(payload.split(opcode, 1)[-1])
                break
        self.assertEqual(called, [])

    def test_empty_payload_does_not_match(self):
        called = []
        opcodes = {"HMKEY:": lambda p: called.append(p)}
        payload = ""
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                handler(payload.split(opcode, 1)[-1])
                break
        self.assertEqual(called, [])

    def test_multiple_opcodes_first_match_wins(self):
        called = []
        opcodes = {
            "HM": lambda p: called.append("HM"),
            "HMKEY:": lambda p: called.append("HMKEY"),
        }
        payload = "HMKEY:val"
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                handler(payload.split(opcode, 1)[-1])
                break
        self.assertEqual(len(called), 1)

    def test_payload_split_extracts_remainder(self):
        result = []
        opcodes = {"HMPSWD:": lambda p: result.append(p)}
        payload = "HMPSWD:secretpassword"
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                result.append(payload.split(opcode, 1)[-1])
                break
        self.assertEqual(result, ["secretpassword"])


# ---------------------------------------------------------------------------
# GGWaveMaster — add_client_callback
# ---------------------------------------------------------------------------

class TestGGWaveMasterCallback(unittest.TestCase):
    """GGWaveMaster.add_client delegates entirely to add_client_callback."""

    def test_callback_called_with_key_and_pswd(self):
        callback = MagicMock()
        master = _make_master(callback)
        master.pswd = "secret123"
        master.add_client("myaccesskey")
        callback.assert_called_once_with("myaccesskey", "secret123")

    def test_client_registered_event_emitted(self):
        callback = MagicMock()
        master = _make_master(callback)
        master.pswd = "pw"
        master.add_client("ak")
        master.bus.emit.assert_called_once()
        event = master.bus.emit.call_args[0][0]
        self.assertEqual(event.msg_type, "hm.ggwave.client_registered")
        self.assertEqual(event.data["key"], "ak")
        self.assertEqual(event.data["pswd"], "pw")

    def test_hivemind_core_never_imported(self):
        """add_client must not import hivemind_core."""
        callback = MagicMock()
        master = _make_master(callback)
        master.pswd = "pw"

        import sys
        modules_before = set(sys.modules.keys())
        master.add_client("key123")
        new_mods = {m for m in set(sys.modules.keys()) - modules_before
                    if "hivemind_core" in m}
        self.assertEqual(new_mods, set())


# ---------------------------------------------------------------------------
# GGWaveMaster — URL opcodes (HMWSP:, HMHTTP:, HMHOST:)
# ---------------------------------------------------------------------------

class TestGGWaveMasterNewOpcodes(unittest.TestCase):

    def test_handle_key_emits_hmhost_only_when_no_ports(self):
        master = _make_master()
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertEqual(emitted, ["HMHOST:192.168.1.1"])

    def test_handle_key_emits_hmwsp_when_ws_port_set(self):
        master = _make_master(ws_port=5678)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMWSP:ws://192.168.1.1:5678", emitted)
        self.assertIn("HMHOST:192.168.1.1", emitted)
        self.assertLess(emitted.index("HMWSP:ws://192.168.1.1:5678"),
                        emitted.index("HMHOST:192.168.1.1"))

    def test_handle_key_emits_hmwsp_ssl(self):
        master = _make_master(ws_port=5678, ws_ssl=True)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMWSP:wss://192.168.1.1:5678", emitted)

    def test_handle_key_emits_hmhttp_when_http_port_set(self):
        master = _make_master(http_port=8080)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMHTTP:http://192.168.1.1:8080", emitted)
        self.assertIn("HMHOST:192.168.1.1", emitted)

    def test_handle_key_emits_hmhttp_ssl(self):
        master = _make_master(http_port=8443, http_ssl=True)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMHTTP:https://192.168.1.1:8443", emitted)

    def test_handle_key_emits_both_ws_and_http(self):
        master = _make_master(ws_port=5678, http_port=8080)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMWSP:ws://192.168.1.1:5678", emitted)
        self.assertIn("HMHTTP:http://192.168.1.1:8080", emitted)
        self.assertIn("HMHOST:192.168.1.1", emitted)
        self.assertLess(emitted.index("HMWSP:ws://192.168.1.1:5678"),
                        emitted.index("HMHTTP:http://192.168.1.1:8080"))
        self.assertLess(emitted.index("HMHTTP:http://192.168.1.1:8080"),
                        emitted.index("HMHOST:192.168.1.1"))


# ---------------------------------------------------------------------------
# GGWaveSlave — _resolve_host and GGWavePresenceSlave
# ---------------------------------------------------------------------------

class TestGGWaveSlaveResolveHost(unittest.TestCase):

    def test_default_resolve_host_returns_payload(self):
        slave = _make_slave()
        self.assertEqual(slave._resolve_host("192.168.1.10"), "192.168.1.10")

    def test_presence_slave_uses_discovered_url_when_set(self):
        from hivemind_ggwave import GGWavePresenceSlave
        slave = _make_slave(GGWavePresenceSlave)
        slave._discovered_url = "wss://192.168.1.5:5679"
        self.assertEqual(slave._resolve_host("10.0.0.1"), "wss://192.168.1.5:5679")

    def test_presence_slave_falls_back_to_payload_when_no_url(self):
        from hivemind_ggwave import GGWavePresenceSlave
        slave = _make_slave(GGWavePresenceSlave)
        self.assertIsNone(slave._discovered_url)
        self.assertEqual(slave._resolve_host("10.0.0.1"), "10.0.0.1")


class TestGGWavePresenceSlaveImportError(unittest.TestCase):
    def test_presence_slave_start_survives_missing_hivemind_presence(self):
        from hivemind_ggwave import GGWavePresenceSlave
        slave = _make_slave(GGWavePresenceSlave)

        real_import = builtins.__import__

        def import_raises_for_presence(name, *args, **kwargs):
            if "hivemind_presence" in name:
                raise ImportError("hivemind-presence not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_raises_for_presence):
            slave.start()  # must not raise

        self.assertIsNone(slave._discovered_url)


# ---------------------------------------------------------------------------
# GGWaveSlave — HMWSP: / HMHTTP: / HMHOST: opcode handling
# ---------------------------------------------------------------------------

class TestGGWaveSlaveNewOpcodes(unittest.TestCase):

    def test_handle_wsp_saves_identity(self):
        slave = _make_slave()
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_wsp("ws://192.168.1.1:5678")
        mock_save.assert_called_once_with("ws://192.168.1.1:5678")

    def test_handle_wsp_sets_ws_url_received(self):
        slave = _make_slave()
        self.assertFalse(slave._ws_url_received)
        with patch.object(slave, "_save_identity"):
            slave.handle_wsp("ws://192.168.1.1:5678")
        self.assertTrue(slave._ws_url_received)

    def test_handle_http_saves_identity_when_no_ws(self):
        slave = _make_slave()
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_http("http://192.168.1.1:8080")
        mock_save.assert_called_once_with("http://192.168.1.1:8080")

    def test_handle_http_ignored_when_ws_already_received(self):
        slave = _make_slave()
        slave._ws_url_received = True
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_http("http://192.168.1.1:8080")
        mock_save.assert_not_called()

    def test_handle_host_ignored_when_ws_already_received(self):
        slave = _make_slave()
        slave._ws_url_received = True
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_host("192.168.1.1")
        mock_save.assert_not_called()

    def test_handle_host_saves_identity(self):
        slave = _make_slave()
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_host("192.168.1.1")
        mock_save.assert_called_once_with("192.168.1.1")

    def test_save_identity_adds_ws_scheme_for_bare_ip(self):
        slave = _make_slave()
        with patch("hivemind_ggwave.NodeIdentity") as MockIdentity:
            instance = MockIdentity.return_value
            instance.IDENTITY_FILE = MagicMock(path="/tmp/id.json")
            slave._save_identity("192.168.1.1")
        self.assertEqual(instance.default_master, "ws://192.168.1.1")

    def test_save_identity_preserves_existing_scheme(self):
        slave = _make_slave()
        with patch("hivemind_ggwave.NodeIdentity") as MockIdentity:
            instance = MockIdentity.return_value
            instance.IDENTITY_FILE = MagicMock(path="/tmp/id.json")
            slave._save_identity("wss://192.168.1.1:5678")
        self.assertEqual(instance.default_master, "wss://192.168.1.1:5678")

    def test_save_identity_http_scheme_preserved(self):
        slave = _make_slave()
        with patch("hivemind_ggwave.NodeIdentity") as MockIdentity:
            instance = MockIdentity.return_value
            instance.IDENTITY_FILE = MagicMock(path="/tmp/id.json")
            slave._save_identity("http://192.168.1.1:8080")
        self.assertEqual(instance.default_master, "http://192.168.1.1:8080")

    def test_wsp_opcode_registered_in_callbacks(self):
        from hivemind_ggwave import GGWaveSlave
        with _ggwave_init_patch():
            slave = GGWaveSlave()
        self.assertIn("HMWSP:", slave.ggwave.OPCODES)

    def test_http_opcode_registered_in_callbacks(self):
        from hivemind_ggwave import GGWaveSlave
        with _ggwave_init_patch():
            slave = GGWaveSlave()
        self.assertIn("HMHTTP:", slave.ggwave.OPCODES)

    def test_wsp_opcode_in_fresh_slave(self):
        from hivemind_ggwave import GGWaveSlave
        with _ggwave_init_patch():
            slave = GGWaveSlave()
        self.assertIn("HMWSP:", slave.ggwave.OPCODES)


if __name__ == "__main__":
    unittest.main()
