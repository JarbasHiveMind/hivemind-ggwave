from os.path import isfile, expanduser
import os
import pexpect
from distutils.spawn import find_executable
from ovos_utils import create_daemon
from hivemind_bus_client.identity import NodeIdentity


class HMGGwaveRx:
    daemon = None
    """
    - master emits a password via ggwave (periodically until an access key is received)
    - devices wanting to connect grab password, generate an access key and send it via ggwave
    - master adds a client with key + password, send an ack (containing host) via ggwave
    - slave devices keep emitting message until they get the ack (then connect to received host)
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.binpath = self.config.get("binary") or \
                       find_executable("ggwave-rx") or \
                       expanduser("~/.local/bin/ggwave-rx")
        if not isfile(self.binpath):
            raise ValueError(f"ggwave-rx not found in {self.binpath}, "
                             f"please install from https://github.com/ggerganov/ggwave")
        self.OPCODES = {
            "HMPSWD:": self.handle_pswd,
            "HMKEY:": self.handle_key,
            "HMHOST:": self.handle_host
        }
        self.daemon = self.daemon or create_daemon(self.monitor_thread)

    def monitor_thread(self):
        child = pexpect.spawn(self.binpath)
        marker = "Received sound data successfully: "
        while True:
            try:
                txt = child.readline().decode("utf-8").strip()
                if txt.startswith(marker):
                    payload = txt.split(marker)[-1][1:-1]
                    for opcode, handler in self.OPCODES.items():
                        if payload.startswith(opcode):
                            p = payload.split(opcode, 1)[-1]
                            handler(p)
                            break
                    else:
                        print(f"invalid ggwave payload: {payload}")
            except pexpect.exceptions.EOF:
                # exited
                print("Exited ggwave-rx process")
                break
            except pexpect.exceptions.TIMEOUT:
                # nothing happened for a while
                pass
            except KeyboardInterrupt:
                break

    def handle_host(self, payload):
        pass

    def handle_key(self, payload):
        pass

    def handle_pswd(self, payload):
        pass


class GGWaveMaster:
    def __init__(self, config=None):
        self.pswd = None
        self.rx = HMGGwaveRx(config)
        self.rx.handle_key = self.handle_key
        self.running = False

    def add_client(self, access_key):

        from hivemind_core.database import ClientDatabase

        key = os.urandom(8).hex()

        with ClientDatabase() as db:
            name = f"HiveMind-Node-{db.total_clients()}"
            db.add_client(name, access_key, crypto_key=key, password=self.pswd)

            # verify
            user = db.get_client_by_api_key(access_key)
            node_id = db.get_item_id(user)

            print("Credentials added to database!\n")
            print("Node ID:", node_id)
            print("Friendly Name:", name)
            print("Access Key:", access_key)
            print("Password:", self.pswd)
            print("Encryption Key:", key)

            print("WARNING: Encryption Key is deprecated, only use if your client does not support password")

    def start(self):
        self.pswd = os.urandom(8).hex()
        self.running = True

    def stop(self):
        self.running = False

    def handle_key(self, payload):
        if self.running:
            self.add_client(payload)
            # TODO emit host


class GGWaveSlave:
    def __init__(self, config=None):
        self.pswd = None
        self.host = None
        self.running = False
        self.rx = HMGGwaveRx(config)
        self.rx.handle_pswd = self.handle_pswd
        self.rx.handle_host = self.handle_host

    def start(self):
        self.running = True
        self.key = os.urandom(8).hex()

    def stop(self):
        self.running = False
        self.host = None
        self.pswd = None
        self.key = None

    def handle_pswd(self, payload):
        if self.running:
            self.pswd = payload
            # TODO - emit key

    def handle_host(self, payload):
        if self.running:
            self.host = payload
            if self.host and self.pswd and self.key:
                identity = NodeIdentity()
                identity.password = self.pswd
                identity.access_key = self.key
                if not self.host.startswith("ws://") and not self.host.startswith("wss://"):
                    self.host = "ws://" + self.host
                identity.default_master = self.host
                identity.save()
                print(f"identity saved: {identity.IDENTITY_FILE.path}")
                self.stop()
