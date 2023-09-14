import os
import time
from distutils.spawn import find_executable
from os.path import isfile, expanduser
from threading import Thread

import pexpect
from hivemind_bus_client.identity import NodeIdentity
from ovos_utils.messagebus import FakeBus, Message
from ovos_utils.network_utils import get_ip


class GGWave(Thread):
    """
    - master emits a password via ggwave (periodically until an access key is received)
    - devices wanting to connect grab password, generate an access key and send it via ggwave
    - master adds a client with key + password, send an ack (containing host) via ggwave
    - slave devices keep emitting message until they get the ack (then connect to received host)
    """

    def __init__(self, config=None):
        super().__init__(daemon=True)
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

    def run(self):
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

    def emit(self, payload):
        print("TODO emit", payload)


class GGWaveMaster(Thread):
    """ run on hivemind-core device
    when loading this class share self.bus to react to events if needed
    eg, start/stop on demand

    if in silent mode the password is assumed to be transmited out of band
    might be a string emitted by the user with another ggwave implementation
    """
    def __init__(self, bus=None, pswd=None, host=None, silent_mode=False, config=None):
        super().__init__()
        self.bus = bus or FakeBus()
        self.host = host
        self.pswd = pswd
        self.rx = GGWave(config)
        self.rx.handle_key = self.handle_key
        self.rx.handle_pswd = self.handle_pswd
        self.running = False
        # if in silent mode the password is assumed to be transmited out of band
        # might be a string emited by the user with another ggwave implementation
        self.silent_mode = silent_mode

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

        self.bus.emit(Message("hm.ggwave.client_registered",
                              {"key": access_key,
                               "pswd": self.pswd,
                               "id": node_id,
                               "name": name}))

    def run(self):
        self.pswd = self.pswd or os.urandom(8).hex()
        self.host = self.host or get_ip()
        self.running = True
        self.bus.emit(Message("hm.ggwave.activated"))
        while self.running:
            time.sleep(3)
            if not self.silent_mode:
                self.rx.emit(f"HMPSWD:{self.pswd}")
                self.bus.emit(Message("hm.ggwave.pswd_emitted"))

    def handle_pswd(self, payload):
        # password shared out of band, silent_mode trigger
        if not self.running and payload == self.pswd:
            self.start()

    def stop(self):
        self.running = False
        self.bus.emit(Message("hm.ggwave.deactivated"))

    def handle_key(self, payload):
        if self.running:
            self.bus.emit(Message("hm.ggwave.key_received"))
            self.add_client(payload)
            self.rx.emit(f"HMHOST:{self.host}")
            self.bus.emit(Message("hm.ggwave.host_emitted"))


class GGWaveSlave:
    """ run on satellite devices
    when loading this class share self.bus to react to events if needed,
    eg connect once entity created """
    def __init__(self, bus=None, config=None):
        self.bus = bus or FakeBus()
        self.pswd = None
        self.key = None
        self.running = False
        self.rx = GGWave(config)
        self.rx.handle_pswd = self.handle_pswd
        self.rx.handle_host = self.handle_host

    def start(self):
        self.running = True
        self.key = os.urandom(8).hex()
        self.bus.emit(Message("hm.ggwave.activated"))

    def stop(self):
        self.running = False
        self.pswd = None
        self.key = None
        self.bus.emit(Message("hm.ggwave.deactivated"))

    def handle_pswd(self, payload):
        if self.running:
            self.pswd = payload
            self.bus.emit(Message("hm.ggwave.pswd_received"))
            self.rx.emit(f"HMKEY:{self.key}")
            self.bus.emit(Message("hm.ggwave.key_emitted"))

    def handle_host(self, payload):
        if self.running:
            host = payload
            self.bus.emit(Message("hm.ggwave.host_received"))
            if host and self.pswd and self.key:
                identity = NodeIdentity()
                identity.password = self.pswd
                identity.access_key = self.key
                if not host.startswith("ws://") and not host.startswith("wss://"):
                    host = "ws://" + host
                identity.default_master = host
                identity.save()
                print(f"identity saved: {identity.IDENTITY_FILE.path}")
                self.bus.emit(Message("hm.ggwave.identity_updated"))
                self.stop()
