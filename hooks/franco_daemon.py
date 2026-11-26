"""Franco daemon: warm edge-tts synthesis + serialized playback on localhost.

Endpoints (all POST endpoints require the X-Franco-Token header):
  POST /say       {"text": str, "lang": str, "voice"?: str} -> queued for synthesis + playback
  POST /silence   stop current playback and clear the queue
  POST /shutdown  silence, then exit (used by `franco_ctl.py stop`)
  GET  /health    {"ok": true, "pid": int, "synth": bool, "playback": bool, "queue": int}

State is written atomically to ~/.franco/daemon.state: {"port", "token", "pid"}.
A lock on ~/.franco/daemon.lock keeps a single daemon per user: a second one
started concurrently exits at once. Runs under pythonw.exe on Windows (no
console). Playback is serialized by one worker thread; barge-in (POST /silence)
stops the audio and drops the queue.
"""

import collections
import json
import os
import re
import secrets
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402
import playback  # noqa: E402

MAX_QUEUE = 3
BUILD = fc.build_id()  # fixed at start: the code this process is actually running
MAX_BODY = fc.MAX_TEXT_LEN * 8
LANG_RE = re.compile(r"[A-Za-z0-9-]{0,20}")
VOICE_RE = re.compile(r"[A-Za-z]{2,3}-[A-Za-z0-9]{2,8}-[A-Za-z0-9]{1,48}")

# Network limits for one synthesis, in seconds.
CONNECT_TIMEOUT = 10
RECEIVE_TIMEOUT = 30
SYNTH_TIMEOUT = 45


def _discard(path):
    try:
        os.unlink(path)
    except OSError:
        pass


def _describe(exc):
    """Short, single-line error description for the log."""
    msg = " ".join(str(exc).split())[:200]
    return "%s: %s" % (type(exc).__name__, msg) if msg else type(exc).__name__


def synthesise_edge_tts(text, voice):
    """Synthesise text to a temporary mp3 and return its path.

    The file is removed again if anything goes wrong, including a timeout.
    """
    import asyncio

    import edge_tts

    fd_, path = tempfile.mkstemp(prefix="franco_", suffix=".mp3")
    os.close(fd_)
    try:
        communicate = edge_tts.Communicate(
            text, voice, connect_timeout=CONNECT_TIMEOUT, receive_timeout=RECEIVE_TIMEOUT
        )
        asyncio.run(asyncio.wait_for(communicate.save(path), SYNTH_TIMEOUT))
        if os.path.getsize(path) == 0:
            raise RuntimeError("the speech service returned no audio")
    except BaseException:
        _discard(path)
        raise
    return path


class Player:
    """Bounded queue + single worker. All queue and "current utterance" state is
    guarded by one condition, so silence() cannot miss an item that is being
    handed from the queue to the worker."""

    def __init__(self, synthesise=None, play=None, max_queue=MAX_QUEUE):
        self._synthesise = synthesise or synthesise_edge_tts
        self._play = play or playback.play
        self.max_queue = max_queue
        self._cond = threading.Condition()
        self._items = collections.deque()
        self._current = None  # threading.Event that stops the current utterance
        self._closed = False
        self.synth_ok = True
        self.playback_ok = True
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    # -- public ------------------------------------------------------------
    def say(self, text, lang, voice=None):
        """Queue an utterance; drop the oldest when full (speech never lags far
        behind). voice overrides the language map. Returns the queue length."""
        with self._cond:
            while len(self._items) >= self.max_queue:
                self._items.popleft()
            self._items.append((text, lang, voice))
            self._cond.notify()
            return len(self._items)

    def silence(self):
        with self._cond:
            self._items.clear()
            if self._current is not None:
                self._current.set()

    def health(self):
        with self._cond:
            queued = len(self._items)
        return {
            "ok": True,
            "pid": os.getpid(),
            "build": BUILD,
            "synth": self.synth_ok,
            "playback": self.playback_ok,
            "queue": queued,
        }

    def close(self, timeout=2.0):
        with self._cond:
            self._closed = True
            self._items.clear()
            if self._current is not None:
                self._current.set()
            self._cond.notify_all()
        self._worker.join(timeout)

    # -- worker ------------------------------------------------------------
    def _loop(self):
        while True:
            with self._cond:
                while not self._items and not self._closed:
                    self._cond.wait()
                if self._closed:
                    return
                text, lang, voice = self._items.popleft()
                stop = threading.Event()
                self._current = stop
            try:
                self._speak(text, lang, voice, stop)
            except Exception as exc:  # noqa: BLE001 — never let the worker die
                fc.log("worker error: %s" % _describe(exc))
            finally:
                with self._cond:
                    self._current = None

    def _speak(self, text, lang, voice, stop):
        voice = voice or fc.voice_for_lang(lang)
        # Metadata only in the log: the spoken text itself is never written to disk.
        meta = "lang=%s voice=%s chars=%d" % (lang or "-", voice, len(text))
        try:
            path = self._synthesise(text, voice)
        except Exception as exc:  # noqa: BLE001
            self.synth_ok = False
            fc.log("synthesis failed %s: %s" % (meta, _describe(exc)))
            return
        self.synth_ok = True
        try:
            if stop.is_set():
                fc.log("spoke %s: interrupted before playback" % meta)
                return
            try:
                completed = self._play(path, stop)
                error = ""
            except Exception as exc:  # noqa: BLE001
                completed, error = False, _describe(exc)
            if completed:
                self.playback_ok = True
                outcome = "ok"
            elif stop.is_set():
                outcome = "interrupted"
            else:
                self.playback_ok = False
                outcome = "FAILED (audio backend %s%s)" % (
                    playback.get_backend(), ": " + error if error else ""
                )
            fc.log("spoke %s: %s" % (meta, outcome))
        finally:
            _discard(path)


class _Handler(BaseHTTPRequestHandler):
    server_version = "Franco"

    def log_message(self, fmt, *args):  # quiet: no console under pythonw
        pass

    # -- helpers -----------------------------------------------------------
    def _authorised(self):
        expected = self.server.token
        given = self.headers.get("X-Franco-Token", "")
        return bool(expected) and secrets.compare_digest(given, expected)

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        """Read the whole request body before any reply: closing a socket with
        unread data makes Windows reset the connection, and the client would
        see an abort instead of the error status. Returns bytes, or None after
        sending an error."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self.close_connection = True
            self._send(400, {"error": "bad content-length"})
            return None
        if length < 0:
            self.close_connection = True
            self._send(400, {"error": "bad content-length"})
            return None
        if length > MAX_BODY:
            remaining = min(length, 1 << 20)  # drain a bounded amount, then give up
            while remaining > 0:
                chunk = self.rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)
            self.close_connection = True
            self._send(413, {"error": "body too large"})
            return None
        return self.rfile.read(length) if length else b""

    def _parse_payload(self, raw):
        """Return the JSON object in the body, or None after sending an error."""
        try:
            payload = json.loads(raw.decode("utf-8")) if raw.strip() else {}
        except (ValueError, UnicodeDecodeError):
            self._send(400, {"error": "bad json"})
            return None
        if not isinstance(payload, dict):
            self._send(400, {"error": "expected a JSON object"})
            return None
        return payload

    # -- routes ------------------------------------------------------------
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send(200, self.server.player.health())
        elif self.path in ("/say", "/silence", "/shutdown"):
            self._send(405, {"error": "POST required"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        raw = self._read_body()
        if raw is None:
            return
        if not self._authorised():
            self._send(403, {"error": "bad token"})
            return
        if self.path not in ("/say", "/silence", "/shutdown"):
            self._send(404, {"error": "not found"})
            return
        payload = self._parse_payload(raw)
        if payload is None:
            return
        player = self.server.player

        if self.path == "/say":
            text, lang = payload.get("text", ""), payload.get("lang", "") or ""
            voice = payload.get("voice") or None
            if not isinstance(text, str) or not isinstance(lang, str) or not LANG_RE.fullmatch(lang):
                self._send(400, {"error": "text and lang must be strings; lang a language tag"})
                return
            if voice is not None and not (isinstance(voice, str) and VOICE_RE.fullmatch(voice)):
                self._send(400, {"error": "voice must be a voice id such as it-IT-ElsaNeural"})
                return
            text = fc.sanitise(text)[: fc.MAX_TEXT_LEN]
            if not text:
                self._send(200, {"ok": True, "skipped": "empty"})
                return
            self._send(200, {"ok": True, "queued": player.say(text, lang, voice)})
        elif self.path == "/silence":
            player.silence()
            self._send(200, {"ok": True})
        else:  # /shutdown
            player.silence()
            self._send(200, {"ok": True})
            # shutdown() blocks until serve_forever() returns: call it off-thread.
            threading.Thread(target=self.server.shutdown, daemon=True).start()


def make_server(player, token, port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
    server.daemon_threads = True
    server.player = player
    server.token = token
    return server


def acquire_single_instance(path):
    """Take an exclusive, non-blocking lock held for the life of the process.
    Returns the open lock file, or None if another daemon holds it."""
    try:
        handle = open(path, "a+b")
    except OSError:
        return None
    try:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def main():
    os.makedirs(fc.CONFIG_DIR, exist_ok=True)
    lock = acquire_single_instance(fc.config_path("daemon.lock"))
    if lock is None:
        fc.log("another daemon is already running; pid %d exits" % os.getpid())
        return

    token = secrets.token_hex(16)
    player = Player()
    server = make_server(player, token)
    port = server.server_address[1]
    fc.write_state({"port": port, "token": token, "pid": os.getpid()})
    fc.log("daemon started on port %d (pid %d)" % (port, os.getpid()))

    def remove_state():
        state = fc.read_daemon_state()
        if state and state.get("pid") == os.getpid():
            try:
                os.unlink(fc.config_path("daemon.state"))
            except OSError:
                pass

    def on_signal(signum, frame):  # noqa: ARG001
        player.silence()
        remove_state()
        sys.exit(0)

    try:
        import signal

        signal.signal(signal.SIGTERM, on_signal)
        signal.signal(signal.SIGINT, on_signal)
    except (ImportError, ValueError):
        pass

    try:
        server.serve_forever()
    finally:
        server.server_close()
        player.close()
        remove_state()
        fc.log("daemon stopped (pid %d)" % os.getpid())
        lock.close()


if __name__ == "__main__":
    main()
