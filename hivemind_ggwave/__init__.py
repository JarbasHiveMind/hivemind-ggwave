import io
import os
import time
import wave
from threading import Thread
from typing import Callable, Dict, Optional

import ggwave
import sounddevice as sd
from hivemind_bus_client.identity import NodeIdentity
from ovos_bus_client.message import Message
from ovos_utils.fakebus import FakeBus
from ovos_utils.log import LOG
from ovos_utils.network_utils import get_ip
from ovos_utils.sound import play_audio

# Audio parameters matching the ggwave defaults
_SAMPLE_RATE: int = 48000
_CHANNELS: int = 1
_BLOCK_SIZE: int = 1024  # frames per read; smaller = lower latency
_DTYPE: str = "float32"


def _encode_wav(samples: bytes, sample_rate: int = _SAMPLE_RATE) -> bytes:
    """Wrap raw float32 PCM *samples* in a WAV container and return the bytes."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(4)  # float32 = 4 bytes per sample
        wf.setframerate(sample_rate)
        wf.writeframes(samples)
    return buf.getvalue()


class GGWave(Thread):
    """Audio-over-sound transceiver using the ``ggwave`` Python bindings.

    The receiver loop captures audio via ``sounddevice`` and feeds each chunk
    to ``ggwave.decode()``.  When a complete payload is recognised, the
    matching opcode handler is called.

    ``emit()`` uses ``ggwave.encode()`` to produce PCM samples, wraps them
    in a WAV container, and plays them via ``ovos_utils.sound.play_audio``.

    Pairing protocol::

        Master → Satellite : HMPSWD:<password>      (broadcast until key received)
        Satellite → Master : HMKEY:<access_key>
        Master → Satellite : HMWSP:<ws[s]://ip:port> (if ws_port given)
        Master → Satellite : HMHTTP:<http[s]://ip:port> (if http_port given)
        Master → Satellite : HMHOST:<ip>            (always, doubles as end-of-handshake marker)

    Args:
        config: Optional dict; supported keys:
            - ``protocol_id`` (int): ggwave transmission protocol (default 1).
            - ``volume`` (int): TX volume 0–100 (default 50).
            - ``sample_rate`` (int): audio sample rate (default 48 000 Hz).
            - ``block_size`` (int): capture block size in frames (default 1024).
            - ``input_device``: sounddevice device index or name for capture.
            - ``output_device``: sounddevice device index or name for playback.
        callbacks: ``{opcode_prefix: handler}`` mapping, e.g.
            ``{"HMPSWD:": self.handle_pswd}``.
        debug: If ``True``, log each decoded payload before dispatch.
    """

    def __init__(self, config: Optional[dict] = None,
                 callbacks: Optional[Dict[str, Callable]] = None,
                 debug: bool = False):
        super().__init__(daemon=True)
        self.config = config or {}
        self.debug = debug
        self.OPCODES: Dict[str, Callable] = callbacks or {}

        self._protocol_id: int = self.config.get("protocol_id", 1)
        self._volume: int = self.config.get("volume", 50)
        self._sample_rate: int = self.config.get("sample_rate", _SAMPLE_RATE)
        self._block_size: int = self.config.get("block_size", _BLOCK_SIZE)
        self._input_device = self.config.get("input_device", None)
        self._output_device = self.config.get("output_device", None)

        self.running: bool = False
        self._ggwave = ggwave.init()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def stop(self) -> None:
        """Signal the receive loop to stop."""
        self.running = False

    def __del__(self) -> None:
        try:
            ggwave.free(self._ggwave)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Receive
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Capture audio and dispatch decoded ggwave payloads to handlers."""
        self.running = True
        try:
            with sd.RawInputStream(
                samplerate=self._sample_rate,
                channels=_CHANNELS,
                dtype=_DTYPE,
                blocksize=self._block_size,
                device=self._input_device,
            ) as stream:
                while self.running:
                    data, overflowed = stream.read(self._block_size)
                    if overflowed:
                        LOG.debug("ggwave: audio input overflow")
                    result = ggwave.decode(self._ggwave, bytes(data))
                    if result is not None:
                        try:
                            payload = result.decode("utf-8")
                        except UnicodeDecodeError:
                            LOG.warning("ggwave: received non-UTF-8 payload, ignoring")
                            continue
                        self._dispatch(payload)
        except Exception:
            LOG.exception("ggwave receive loop error")
        finally:
            self.running = False

    def _dispatch(self, payload: str) -> None:
        """Route *payload* to the matching opcode handler."""
        if self.debug:
            LOG.debug(f"ggwave payload: {payload!r}")
        for opcode, handler in self.OPCODES.items():
            if payload.startswith(opcode):
                arg = payload[len(opcode):]
                handler(arg)
                return
        LOG.warning(f"ggwave: unrecognised payload: {payload!r}")

    # ------------------------------------------------------------------
    # Transmit
    # ------------------------------------------------------------------

    def emit(self, payload: str) -> None:
        """Encode *payload* with ggwave and play it through the audio output.

        The encoded float32 PCM samples are wrapped in a WAV container and
        played back via :func:`ovos_utils.sound.play_audio`.

        Args:
            payload: ASCII string to transmit (e.g. ``"HMPSWD:secret"``).
        """
        LOG.debug(f"ggwave emit: {payload!r}")
        try:
            samples: bytes = ggwave.encode(
                payload,
                protocolId=self._protocol_id,
                volume=self._volume,
            )
            wav_bytes = _encode_wav(samples, self._sample_rate)
            play_audio(io.BytesIO(wav_bytes)).wait()
        except Exception:
            LOG.exception(f"ggwave emit failed for payload {payload!r}")


class GGWaveMaster(Thread):
    """Hub-side GGWave pairing handler.

    Runs on the hivemind-core device.  Broadcasts the pairing password
    periodically until a satellite sends back its access key, then registers
    the new client and confirms the hub address.

    If *silent_mode* is ``True`` the password is not broadcast over audio —
    it must be conveyed out-of-band (e.g. shown in a browser or logged).

    Args:
        bus: Optional message bus; a :class:`FakeBus` is created if not given.
        pswd: Pairing password.  A random 8-byte hex string is used if
            ``None``.
        host: Hub IP to broadcast.  Auto-detected via
            :func:`~ovos_utils.network_utils.get_ip` if ``None``.
        silent_mode: If ``True``, skip the audio password broadcast.
        config: Forwarded to :class:`GGWave`.
        add_client_callback: If set, called as ``callback(access_key, pswd)``
            instead of importing :class:`hivemind_core.database.ClientDatabase`.
        ws_port: If given, emits ``HMWSP:ws[s]://<host>:<port>`` so satellites
            learn the exact WebSocket URL.
        ws_ssl: Whether the WebSocket server uses SSL (``wss://``).
        http_port: If given, emits ``HMHTTP:http[s]://<host>:<port>``.
        http_ssl: Whether the HTTP server uses SSL (``https://``).
    """

    def __init__(self, bus=None, pswd: Optional[str] = None,
                 host: Optional[str] = None,
                 silent_mode: bool = False,
                 config: Optional[dict] = None,
                 add_client_callback: Optional[Callable] = None,
                 ws_port: Optional[int] = None,
                 ws_ssl: bool = False,
                 http_port: Optional[int] = None,
                 http_ssl: bool = False):
        super().__init__(daemon=True)
        self.bus = bus or FakeBus()
        self.host = host
        self.pswd = pswd
        self.add_client_callback = add_client_callback
        self.ws_port = ws_port
        self.ws_ssl = ws_ssl
        self.http_port = http_port
        self.http_ssl = http_ssl
        self.silent_mode = silent_mode

        callbacks = {"HMKEY:": self.handle_key}
        self.ggwave = GGWave(config, callbacks)

    def add_client(self, access_key: str) -> None:
        """Register a new satellite client.

        If *add_client_callback* was provided, it is called; otherwise
        :class:`hivemind_core.database.ClientDatabase` is used directly.

        Args:
            access_key: The access key received from the satellite.
        """
        if self.add_client_callback is not None:
            self.add_client_callback(access_key, self.pswd)
            self.bus.emit(Message("hm.ggwave.client_registered",
                                  {"key": access_key, "pswd": self.pswd}))
            return

        from hivemind_core.database import ClientDatabase

        crypto_key = os.urandom(8).hex()
        with ClientDatabase() as db:
            name = f"HiveMind-Node-{db.total_clients()}"
            db.add_client(name, access_key, crypto_key=crypto_key,
                          password=self.pswd)
            user = db.get_client_by_api_key(access_key)
            node_id = db.get_item_id(user)
            LOG.info(f"Client registered in database: {access_key}")

        self.bus.emit(Message("hm.ggwave.client_registered",
                              {"key": access_key,
                               "pswd": self.pswd,
                               "id": node_id,
                               "name": name}))

    def run(self) -> None:
        """Start the GGWave receiver and broadcast the password periodically."""
        self.ggwave.start()
        LOG.info("GGWaveMaster: activated")
        self.pswd = self.pswd or os.urandom(8).hex()
        self.host = self.host or get_ip()
        self.bus.emit(Message("hm.ggwave.activated"))
        if self.silent_mode:
            LOG.info(f"Silent mode — emit HMPSWD:{self.pswd} out-of-band")
        while self.ggwave.running:
            time.sleep(5)
            if not self.silent_mode:
                LOG.info("GGWaveMaster: broadcasting password")
                self.ggwave.emit(f"HMPSWD:{self.pswd}")
                self.bus.emit(Message("hm.ggwave.pswd_emitted"))

    def stop(self) -> None:
        """Stop the GGWave receiver and emit the deactivated event."""
        self.ggwave.stop()
        self.bus.emit(Message("hm.ggwave.deactivated"))
        LOG.info("GGWaveMaster: deactivated")

    def handle_key(self, payload: str) -> None:
        """Called when a satellite broadcasts ``HMKEY:<access_key>``.

        Registers the client, then broadcasts the hub URL(s) back.

        Args:
            payload: The access key string received from the satellite.
        """
        if self.ggwave.running:
            self.bus.emit(Message("hm.ggwave.key_received"))
            self.add_client(payload)
            if self.ws_port:
                scheme = "wss" if self.ws_ssl else "ws"
                self.ggwave.emit(f"HMWSP:{scheme}://{self.host}:{self.ws_port}")
            if self.http_port:
                scheme = "https" if self.http_ssl else "http"
                self.ggwave.emit(f"HMHTTP:{scheme}://{self.host}:{self.http_port}")
            self.ggwave.emit(f"HMHOST:{self.host}")  # backward compat
            self.bus.emit(Message("hm.ggwave.host_emitted"))


class GGWaveSlave:
    """Satellite-side GGWave pairing handler.

    Listens for the hub password, sends back its access key, then waits for
    the hub address and saves it as the default ``NodeIdentity``.

    Args:
        key: Access key to send to the hub.  A random 8-byte hex string is
            generated if ``None``.
        bus: Optional message bus.
        config: Forwarded to :class:`GGWave`.
    """

    def __init__(self, key: Optional[str] = None, bus=None,
                 config: Optional[dict] = None):
        self.bus = bus or FakeBus()
        self.pswd: Optional[str] = None
        self.key: Optional[str] = key or os.urandom(8).hex()
        self._ws_url_received: bool = False
        callbacks = {
            "HMPSWD:": self.handle_pswd,
            "HMWSP:": self.handle_wsp,
            "HMHTTP:": self.handle_http,
            "HMHOST:": self.handle_host,
        }
        self.ggwave = GGWave(config, callbacks)

    def start(self) -> None:
        """Start the GGWave receiver."""
        self.ggwave.start()
        self.bus.emit(Message("hm.ggwave.activated"))
        LOG.info("GGWaveSlave: activated")

    def stop(self) -> None:
        """Stop the GGWave receiver."""
        self.ggwave.stop()
        self.pswd = None
        self.key = None
        self.bus.emit(Message("hm.ggwave.deactivated"))
        LOG.info("GGWaveSlave: deactivated")

    def handle_pswd(self, payload: str) -> None:
        """Handle ``HMPSWD:<password>`` — store password and reply with the access key.

        Args:
            payload: The pairing password broadcast by the hub.
        """
        LOG.info("GGWaveSlave: password received")
        if self.ggwave.running:
            self.pswd = payload
            self.bus.emit(Message("hm.ggwave.pswd_received"))
            self.ggwave.emit(f"HMKEY:{self.key}")
            self.bus.emit(Message("hm.ggwave.key_emitted"))

    def _resolve_host(self, payload: str) -> str:
        """Return the URL to store from a bare ``HMHOST:`` payload.

        Override in subclasses to substitute a pre-discovered URL (e.g. from
        hivemind-presence) that includes the correct port.

        Args:
            payload: The raw payload string following the ``HMHOST:`` opcode.

        Returns:
            URL string to use as ``NodeIdentity.default_master``.
        """
        return payload

    def _save_identity(self, host: str) -> None:
        """Normalise *host* to a URL, persist the ``NodeIdentity``, and stop.

        Args:
            host: Host IP or full URL received from the hub.
        """
        if host and self.pswd and self.key:
            identity = NodeIdentity()
            identity.password = self.pswd
            identity.access_key = self.key
            if not host.startswith(("ws://", "wss://", "http://", "https://")):
                host = "ws://" + host
            identity.default_master = host
            identity.save()
            LOG.info(f"GGWaveSlave: identity saved to {identity.IDENTITY_FILE.path}")
            self.bus.emit(Message("hm.ggwave.identity_updated"))
            self.stop()

    def handle_wsp(self, payload: str) -> None:
        """Handle ``HMWSP:<url>`` — full WebSocket URL including port.

        Takes priority over ``HMHTTP:`` and ``HMHOST:``.

        Args:
            payload: Full WebSocket URL, e.g. ``ws://192.168.1.1:5678``.
        """
        if self.ggwave.running:
            LOG.info(f"GGWaveSlave: WebSocket URL received: {payload}")
            self.bus.emit(Message("hm.ggwave.host_received"))
            self._ws_url_received = True
            self._save_identity(payload)

    def handle_http(self, payload: str) -> None:
        """Handle ``HMHTTP:<url>`` — full HTTP URL (used if no WS URL was received).

        Args:
            payload: Full HTTP URL, e.g. ``http://192.168.1.1:8080``.
        """
        if self.ggwave.running and not self._ws_url_received:
            LOG.info(f"GGWaveSlave: HTTP URL received: {payload}")
            self.bus.emit(Message("hm.ggwave.host_received"))
            self._save_identity(payload)

    def handle_host(self, payload: str) -> None:
        """Handle ``HMHOST:<ip>`` — bare IP, legacy backward-compat opcode.

        Ignored if a WebSocket URL was already received via ``HMWSP:``.

        Args:
            payload: Bare IP address broadcast by the hub.
        """
        if self.ggwave.running and not self._ws_url_received:
            host = self._resolve_host(payload)
            LOG.info(f"GGWaveSlave: host received: {payload}")
            self.bus.emit(Message("hm.ggwave.host_received"))
            self._save_identity(host)


class GGWavePresenceSlave(GGWaveSlave):
    """``GGWaveSlave`` that pre-discovers the hub via UPnP/Zeroconf.

    Uses ``hivemind-presence`` to scan for the hub before starting the audio
    pairing exchange.  If hivemind-presence is not installed, or no hub is
    found within *presence_timeout* seconds, falls back to the bare IP from
    the ``HMHOST:`` payload.

    Args:
        key: Access key to send to the hub.
        bus: Optional message bus.
        config: Forwarded to :class:`GGWave`.
        presence_timeout: Seconds to scan via hivemind-presence (default 25).
    """

    def __init__(self, key: Optional[str] = None, bus=None,
                 config: Optional[dict] = None,
                 presence_timeout: float = 25.0):
        super().__init__(key, bus, config)
        self._discovered_url: Optional[str] = None
        self._presence_timeout = presence_timeout

    def start(self) -> None:
        """Scan for the hub via hivemind-presence, then start GGWave."""
        try:
            from hivemind_presence import LocalDiscovery
            disc = LocalDiscovery()
            for node in disc.scan(timeout=self._presence_timeout):
                scheme = "wss" if node.ssl else "ws"
                self._discovered_url = f"{scheme}://{node.host}:{node.port}"
                LOG.info(f"GGWavePresenceSlave: discovered {self._discovered_url}")
                disc.stop()
                break
        except ImportError:
            LOG.warning("hivemind-presence not installed; using HMHOST payload directly")
        super().start()

    def _resolve_host(self, payload: str) -> str:
        """Return the pre-discovered URL, or *payload* if nothing was found."""
        return self._discovered_url or payload
