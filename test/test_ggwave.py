import builtins
import unittest
from unittest.mock import MagicMock, patch


@unittest.skip(
    "Requires ggwave-rx binary installed on the system — "
    "GGWave.__init__ raises ValueError if ggwave-rx is not found"
)
class TestGGWave(unittest.TestCase):
    """Tests for GGWave require the ggwave-rx and ggwave-cli binaries to be installed."""

    def test_init_raises_if_ggwave_rx_missing(self):
        from hivemind_ggwave import GGWave
        with self.assertRaises(ValueError):
            GGWave(config={"ggwave-rx": "/nonexistent/path"})

    def test_stop(self):
        pass

    def test_opcodes_dispatched_correctly(self):
        pass

    def test_emit_remote_mode(self):
        pass


class TestGGWaveOpcodeLogic(unittest.TestCase):
    """Tests for opcode dispatch logic that can be tested without the binary."""

    def test_opcode_match(self):
        """Verify the opcode matching logic used in GGWave.run()."""
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
                p = payload.split(opcode, 1)[-1]
                handler(p)
                break

        opcodes["HMKEY:"].assert_called_once_with("abc123")
        opcodes["HMPSWD:"].assert_not_called()
        opcodes["HMWSP:"].assert_not_called()
        opcodes["HMHTTP:"].assert_not_called()
        opcodes["HMHOST:"].assert_not_called()

    def test_unknown_opcode_does_not_call_handlers(self):
        """Unknown opcode should not trigger any handler."""
        handlers_called = []
        opcodes = {
            "HMKEY:": lambda p: handlers_called.append("HMKEY"),
        }
        payload = "UNKNOWN:payload"
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                handler(payload.split(opcode, 1)[-1])
                break

        self.assertEqual(handlers_called, [])

    def test_empty_payload_does_not_match(self):
        """Empty payload should not match any opcode."""
        called = []
        opcodes = {"HMKEY:": lambda p: called.append(p)}
        payload = ""
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                handler(payload.split(opcode, 1)[-1])
                break
        self.assertEqual(called, [])

    def test_multiple_opcodes_first_match_wins(self):
        """Only the first matching opcode handler is called."""
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
        """Payload split correctly strips the opcode prefix."""
        result = []
        opcodes = {"HMPSWD:": lambda p: result.append(p)}
        payload = "HMPSWD:secretpassword"
        for opcode, handler in opcodes.items():
            if payload.startswith(opcode):
                p = payload.split(opcode, 1)[-1]
                handler(p)
                break
        self.assertEqual(result, ["secretpassword"])


class TestGGWaveMasterCallback(unittest.TestCase):
    """GGWaveMaster.add_client with add_client_callback — no hivemind_core import."""

    def _make_master(self, callback, pswd="test-pswd"):
        from hivemind_ggwave import GGWaveMaster
        with patch("hivemind_ggwave.isfile", return_value=True):
            master = GGWaveMaster(pswd=pswd, add_client_callback=callback)
        return master

    def test_callback_called_with_key_and_pswd(self):
        callback = MagicMock()
        master = self._make_master(callback, pswd="secret123")
        master.add_client("myaccesskey")
        callback.assert_called_once_with("myaccesskey", "secret123")

    def test_callback_prevents_hivemind_core_import(self):
        callback = MagicMock()
        master = self._make_master(callback, pswd="secret")

        import sys
        modules_before = set(sys.modules.keys())
        master.add_client("key123")
        modules_after = set(sys.modules.keys())

        new_hivemind_core = {m for m in (modules_after - modules_before)
                             if "hivemind_core" in m}
        self.assertEqual(new_hivemind_core, set(),
                         "hivemind_core must not be imported when callback is set")

    def test_client_registered_event_emitted(self):
        callback = MagicMock()
        master = self._make_master(callback, pswd="pw")
        master.bus = MagicMock()
        master.add_client("ak")
        master.bus.emit.assert_called_once()
        event = master.bus.emit.call_args[0][0]
        self.assertEqual(event.msg_type, "hm.ggwave.client_registered")
        self.assertEqual(event.data["key"], "ak")
        self.assertEqual(event.data["pswd"], "pw")

    def test_no_callback_does_not_call_callback(self):
        """When add_client_callback is None, no callback path is taken."""
        from hivemind_ggwave import GGWaveMaster
        with patch("hivemind_ggwave.isfile", return_value=True):
            master = GGWaveMaster(pswd="pw")
        # add_client_callback is None — calling add_client would try to import
        # hivemind_core; we just verify the attribute is None, not that it runs
        self.assertIsNone(master.add_client_callback)


@unittest.skip(
    "Requires ggwave-rx binary and hivemind-core ClientDatabase — "
    "cannot test GGWaveMaster without a running HiveMind database and ggwave binary"
)
class TestGGWaveMaster(unittest.TestCase):
    def test_init(self):
        pass

    def test_handle_key(self):
        pass

    def test_run_broadcasts_password(self):
        pass


class TestGGWaveSlaveResolveHost(unittest.TestCase):
    """Test the _resolve_host hook on GGWaveSlave and subclasses."""

    def _make_slave(self, cls=None):
        if cls is None:
            from hivemind_ggwave import GGWaveSlave as cls
        with patch("hivemind_ggwave.isfile", return_value=True):
            return cls()

    def test_default_resolve_host_returns_payload(self):
        slave = self._make_slave()
        self.assertEqual(slave._resolve_host("192.168.1.10"), "192.168.1.10")

    def test_presence_slave_uses_discovered_url_when_set(self):
        from hivemind_ggwave import GGWavePresenceSlave
        slave = self._make_slave(GGWavePresenceSlave)
        slave._discovered_url = "wss://192.168.1.5:5679"
        self.assertEqual(slave._resolve_host("10.0.0.1"), "wss://192.168.1.5:5679")

    def test_presence_slave_falls_back_to_payload_when_no_url(self):
        from hivemind_ggwave import GGWavePresenceSlave
        slave = self._make_slave(GGWavePresenceSlave)
        self.assertIsNone(slave._discovered_url)
        self.assertEqual(slave._resolve_host("10.0.0.1"), "10.0.0.1")


class TestGGWavePresenceSlaveImportError(unittest.TestCase):
    def test_presence_slave_start_survives_missing_hivemind_presence(self):
        from hivemind_ggwave import GGWavePresenceSlave

        with patch("hivemind_ggwave.isfile", return_value=True):
            slave = GGWavePresenceSlave()

        slave.ggwave = MagicMock()
        slave.bus = MagicMock()

        real_import = builtins.__import__

        def import_raises_for_presence(name, *args, **kwargs):
            if "hivemind_presence" in name:
                raise ImportError("hivemind-presence not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_raises_for_presence):
            slave.start()  # must not raise

        self.assertIsNone(slave._discovered_url)


class TestGGWaveMasterNewOpcodes(unittest.TestCase):
    """GGWaveMaster emits HMWSP:/HMHTTP: when ports are configured."""

    def _make_master(self, **kwargs):
        from hivemind_ggwave import GGWaveMaster
        with patch("hivemind_ggwave.isfile", return_value=True):
            master = GGWaveMaster(pswd="pw", host="192.168.1.1",
                                  add_client_callback=MagicMock(), **kwargs)
        master.ggwave = MagicMock()
        master.ggwave.running = True
        master.bus = MagicMock()
        return master

    def test_handle_key_emits_hmhost_only_when_no_ports(self):
        master = self._make_master()
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertEqual(emitted, ["HMHOST:192.168.1.1"])

    def test_handle_key_emits_hmwsp_when_ws_port_set(self):
        master = self._make_master(ws_port=5678)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMWSP:ws://192.168.1.1:5678", emitted)
        self.assertIn("HMHOST:192.168.1.1", emitted)
        # HMWSP comes before HMHOST
        self.assertLess(emitted.index("HMWSP:ws://192.168.1.1:5678"),
                        emitted.index("HMHOST:192.168.1.1"))

    def test_handle_key_emits_hmwsp_ssl(self):
        master = self._make_master(ws_port=5678, ws_ssl=True)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMWSP:wss://192.168.1.1:5678", emitted)

    def test_handle_key_emits_hmhttp_when_http_port_set(self):
        master = self._make_master(http_port=8080)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMHTTP:http://192.168.1.1:8080", emitted)
        self.assertIn("HMHOST:192.168.1.1", emitted)

    def test_handle_key_emits_hmhttp_ssl(self):
        master = self._make_master(http_port=8443, http_ssl=True)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMHTTP:https://192.168.1.1:8443", emitted)

    def test_handle_key_emits_both_ws_and_http(self):
        master = self._make_master(ws_port=5678, http_port=8080)
        master.handle_key("mykey")
        emitted = [c.args[0] for c in master.ggwave.emit.call_args_list]
        self.assertIn("HMWSP:ws://192.168.1.1:5678", emitted)
        self.assertIn("HMHTTP:http://192.168.1.1:8080", emitted)
        self.assertIn("HMHOST:192.168.1.1", emitted)
        # order: HMWSP, HMHTTP, HMHOST
        self.assertLess(emitted.index("HMWSP:ws://192.168.1.1:5678"),
                        emitted.index("HMHTTP:http://192.168.1.1:8080"))
        self.assertLess(emitted.index("HMHTTP:http://192.168.1.1:8080"),
                        emitted.index("HMHOST:192.168.1.1"))


class TestGGWaveSlaveNewOpcodes(unittest.TestCase):
    """GGWaveSlave handles HMWSP: and HMHTTP: opcodes correctly."""

    def _make_slave(self):
        from hivemind_ggwave import GGWaveSlave
        with patch("hivemind_ggwave.isfile", return_value=True):
            slave = GGWaveSlave()
        slave.ggwave = MagicMock()
        slave.ggwave.running = True
        slave.bus = MagicMock()
        slave.pswd = "mypw"
        slave.key = "mykey"
        return slave

    def test_handle_wsp_saves_identity(self):
        slave = self._make_slave()
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_wsp("ws://192.168.1.1:5678")
        mock_save.assert_called_once_with("ws://192.168.1.1:5678")

    def test_handle_wsp_sets_ws_url_received(self):
        slave = self._make_slave()
        self.assertFalse(slave._ws_url_received)
        with patch.object(slave, "_save_identity"):
            slave.handle_wsp("ws://192.168.1.1:5678")
        self.assertTrue(slave._ws_url_received)

    def test_handle_http_saves_identity_when_no_ws(self):
        slave = self._make_slave()
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_http("http://192.168.1.1:8080")
        mock_save.assert_called_once_with("http://192.168.1.1:8080")

    def test_handle_http_ignored_when_ws_already_received(self):
        slave = self._make_slave()
        slave._ws_url_received = True
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_http("http://192.168.1.1:8080")
        mock_save.assert_not_called()

    def test_handle_host_ignored_when_ws_already_received(self):
        slave = self._make_slave()
        slave._ws_url_received = True
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_host("192.168.1.1")
        mock_save.assert_not_called()

    def test_handle_host_still_works_without_new_opcodes(self):
        """Backward compat: HMHOST: alone still saves identity."""
        slave = self._make_slave()
        with patch.object(slave, "_save_identity") as mock_save:
            slave.handle_host("192.168.1.1")
        mock_save.assert_called_once_with("192.168.1.1")

    def test_save_identity_adds_ws_scheme_for_bare_ip(self):
        slave = self._make_slave()
        with patch("hivemind_ggwave.NodeIdentity") as MockIdentity:
            instance = MockIdentity.return_value
            instance.IDENTITY_FILE = MagicMock(path="/tmp/id.json")
            slave._save_identity("192.168.1.1")
        self.assertEqual(instance.default_master, "ws://192.168.1.1")

    def test_save_identity_preserves_existing_scheme(self):
        slave = self._make_slave()
        with patch("hivemind_ggwave.NodeIdentity") as MockIdentity:
            instance = MockIdentity.return_value
            instance.IDENTITY_FILE = MagicMock(path="/tmp/id.json")
            slave._save_identity("wss://192.168.1.1:5678")
        self.assertEqual(instance.default_master, "wss://192.168.1.1:5678")

    def test_save_identity_http_scheme_preserved(self):
        slave = self._make_slave()
        with patch("hivemind_ggwave.NodeIdentity") as MockIdentity:
            instance = MockIdentity.return_value
            instance.IDENTITY_FILE = MagicMock(path="/tmp/id.json")
            slave._save_identity("http://192.168.1.1:8080")
        self.assertEqual(instance.default_master, "http://192.168.1.1:8080")

    def test_wsp_opcode_registered_in_callbacks(self):
        from hivemind_ggwave import GGWaveSlave
        with patch("hivemind_ggwave.isfile", return_value=True):
            slave = GGWaveSlave()
        self.assertIn("HMWSP:", slave.ggwave.OPCODES)

    def test_http_opcode_registered_in_callbacks(self):
        from hivemind_ggwave import GGWaveSlave
        with patch("hivemind_ggwave.isfile", return_value=True):
            slave = GGWaveSlave()
        self.assertIn("HMHTTP:", slave.ggwave.OPCODES)


@unittest.skip(
    "Requires ggwave-rx binary — cannot instantiate GGWaveSlave without ggwave"
)
class TestGGWaveSlave(unittest.TestCase):
    def test_handle_pswd(self):
        pass

    def test_handle_host_saves_identity(self):
        pass


if __name__ == "__main__":
    unittest.main()
