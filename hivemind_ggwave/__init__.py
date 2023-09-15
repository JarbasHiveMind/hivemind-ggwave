import os
import time
import wave
from distutils.spawn import find_executable
from os.path import isfile, expanduser
from threading import Thread

import pexpect
import requests
from hivemind_bus_client.identity import NodeIdentity
from ovos_utils.file_utils import get_temp_path
from ovos_utils.log import LOG
from ovos_utils.messagebus import FakeBus, Message
from ovos_utils.network_utils import get_ip
from ovos_utils.sound import play_audio


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
        self.rx = self.config.get("ggwave-rx") or \
                  find_executable("ggwave-rx") or \
                  expanduser("~/.local/bin/ggwave-rx")
        self.tx = self.config.get("ggwave-cli") or \
                  find_executable("ggwave-cli") or \
                  expanduser("~/.local/bin/ggwave-cli")
        if not isfile(self.rx):
            raise ValueError(f"ggwave-rx not found in {self.rx}, "
                             f"please install from https://github.com/ggerganov/ggwave")

        self.OPCODES = {
            "HMPSWD:": self.handle_pswd,
            "HMKEY:": self.handle_key,
            "HMHOST:": self.handle_host
        }
        self.running = False
        self.remote = self.config.get("remote", False)
        if not isfile(self.tx):
            LOG.warning("ggwave-cli not found, forcing remote usage")
            self.remote = True

    def stop(self):
        self.running = False

    def run(self):
        self.running = True
        child = pexpect.spawn(self.rx)
        marker = "Received sound data successfully: "
        while self.running:
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
                       LOG.error(f"invalid ggwave payload: {payload}")
            except pexpect.exceptions.EOF:
                # exited
                LOG.debug("Exited ggwave-rx process")
                break
            except pexpect.exceptions.TIMEOUT:
                # nothing happened for a while
                pass
            except KeyboardInterrupt:
                break
        child.close(True)

    def handle_host(self, payload):
        pass

    def handle_key(self, payload):
        pass

    def handle_pswd(self, payload):
        pass

    def emit(self, payload):
        if self.remote:
            tmp = get_temp_path("ggwave")
            wav = self.encode2wave(payload,
                                   f'{tmp}/{payload.replace(":", "_").replace("/", "_")}.wav')
            play_audio(wav).wait()
        else:
            p = pexpect.spawn(f"{self.tx}")
            p.expect("Enter text:")
            p.sendline(payload)
            p.expect("Enter text:")
            time.sleep(5)
            p.close(True)

    def encode2wave(self, message: str,
                    wav_path: str,
                    protocolId: int = 1,
                    sampleRate: float = 48000,
                    volume: int = 50,
                    payloadLength: int = -1,
                    useDSS: int = 0):
        url = 'https://ggwave-to-file.ggerganov.com/'
        params = {
            'm': message,  # message to encode
            'p': protocolId,  # transmission protocol to use
            's': sampleRate,  # output sample rate
            'v': volume,  # output volume
            'l': payloadLength,  # if positive - use fixed-length encoding
            'd': useDSS,  # if positive - use DSS
        }

        response = requests.get(url, params=params)
        if response == '' or b'Usage: ggwave-to-file' in response.content:
            raise SyntaxError('Request failed')

        with wave.open(wav_path, 'wb') as f:
            f.setnchannels(1)
            f.setframerate(sampleRate)
            f.setsampwidth(2)
            f.writeframes(response.content)
        return wav_path


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
        self.ggwave = GGWave(config)
        self.ggwave.handle_key = self.handle_key
        self.ggwave.handle_pswd = self.handle_pswd
        self.ggwave.start()

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

            LOG.info(f"Credentials added to database! {access_key}")

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
                self.ggwave.emit(f"HMPSWD:{self.pswd}")
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
            self.ggwave.emit(f"HMHOST:{self.host}")
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
        self.ggwave = GGWave(config)
        self.ggwave.handle_pswd = self.handle_pswd
        self.ggwave.handle_host = self.handle_host
        self.ggwave.start()

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
            self.ggwave.emit(f"HMKEY:{self.key}")
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
                LOG.info(f"identity saved: {identity.IDENTITY_FILE.path}")
                self.bus.emit(Message("hm.ggwave.identity_updated"))
                self.stop()
