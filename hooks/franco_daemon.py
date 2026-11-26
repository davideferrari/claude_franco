"""Franco daemon: warm edge-tts synthesis + serialized playback on localhost.

Endpoints (all require the X-Franco-Token header, except /health):
  GET  /say?...   not used — say is POST-only
  POST /say       {"text": str, "lang": str}  -> queued for synthesis+playback
  POST /silence   stop current playback and clear the queue
  POST /shutdown  silence, then exit (used by `franco_ctl.py stop`)
  GET  /health    {"ok": true, "synth": bool, "queue": int}

State is written to ~/.franco/daemon.state: {"port": ..., "token": ...}.
Runs under pythonw.exe on Windows (no console). Playback is serialized by a
single worker thread; barge-in (POST /silence) stops audio and drops the queue.
"""

import json
import os
import queue
import secrets
import socket
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402
import playback  # noqa: E402

MAX_QUEUE = 3


class _Stopper:
    """Thread-safe handle to interrupt the currently playing utterance."""

    def __init__(self):
        self._event = threading.Event()

    def event(self):
        return self._event

    def stop(self):
        self._event.set()


class _Player:
    def __init__(self):
        self.queue = queue.Queue()
        self.current = None  # _Stopper for the utterance being played
        self.lock = threading.Lock()
        self.synth_ok = True
        self.synth_error = ""
        self.worker = threading.Thread(target=self._loop, daemon=True)
        self.worker.start()

    # -- worker ------------------------------------------------------------
    def _loop(self):
        while True:
            item = self.queue.get()
            if item is None:
                continue
            text, lang = item
            self._speak(text, lang)

    def _speak(self, text, lang):
        stopper = _Stopper()
        with self.lock:
            self.current = stopper
        try:
            path = self._synthesise(text, lang)
        except Exception as exc:  # noqa: BLE001 — never crash the daemon
            self.synth_ok = False
            self.synth_error = str(exc)
            self._log("synth failed: %s" % exc)
            with self.lock:
                self.current = None
            return
        if stopper.event().is_set():  # barged in during synthesis
            self._log("spoke lang=%s chars=%d: interrupted before playback" % (lang or "-", len(text)))
            _discard(path)
            with self.lock:
                self.current = None
            return
        try:
            completed = playback.play(path, stopper.event())
            # Metadata only: the spoken text itself is never written to disk.
            if completed:
                outcome = "ok"
            elif stopper.event().is_set():
                outcome = "interrupted"
            else:
                outcome = "FAILED (audio backend %s)" % playback.get_backend()
            self._log("spoke lang=%s voice=%s chars=%d: %s"
                      % (lang or "-", fc.voice_for_lang(lang), len(text), outcome))
        except Exception as exc:  # noqa: BLE001
            self._log("playback failed: %s" % exc)
        _discard(path)
        with self.lock:
            self.current = None

    def _synthesise(self, text, lang):
        import edge_tts

        voice = fc.voice_for_lang(lang)
        fd, path = tempfile.mkstemp(prefix="franco_", suffix=".mp3")
        os.close(fd)
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                edge_tts.Communicate(text, voice, rate="+0%").save(path)
            )
        finally:
            loop.close()
        return path

    # -- public ------------------------------------------------------------
    def say(self, text, lang):
        # Drop the oldest if the queue is full (speech never lags far behind).
        try:
            self.queue.put_nowait((text, lang))
        except queue.Full:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                pass
            self.queue.put((text, lang))

    def silence(self):
        with self.lock:
            current = self.current
        if current:
            current.stop()
        while True:
            try:
                self.queue.get_nowait()
            except queue.Empty:
                break

    @staticmethod
    def _log(msg):
        try:
            with open(fc.config_path("daemon.log"), "a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except OSError:
            pass


def _discard(path):
    try:
        os.unlink(path)
    except OSError:
        pass


class _Handler(BaseHTTPRequestHandler):
    player = None  # injected in main()
    token = ""

    def log_message(self, fmt, *args):  # quiet: no console under pythonw
        pass

    # -- helpers -----------------------------------------------------------
    def _authorised(self):
        if not self.token:
            return True
        return self.headers.get("X-Franco-Token", "") == self.token

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # -- routes ------------------------------------------------------------
    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send(200, {
                "ok": True,
                "synth": self.player.synth_ok,
                "queue": self.player.queue.qsize(),
            })
        elif self.path in ("/say", "/silence", "/shutdown"):
            self._send(405, {"error": "POST required"})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):  # noqa: N802
        if not self._authorised():
            self._send(403, {"error": "bad token"})
            return
        length = min(int(self.headers.get("Content-Length", 0) or 0), fc.MAX_TEXT_LEN * 8)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._send(400, {"error": "bad json"})
            return

        if self.path == "/say":
            text = fc.sanitise(str(payload.get("text", "")))[: fc.MAX_TEXT_LEN]
            lang = str(payload.get("lang", "") or "")
            if not text:
                self._send(200, {"ok": True, "skipped": "empty"})
            else:
                self.player.say(text, lang)
                self._send(200, {"ok": True, "queued": self.player.queue.qsize()})
        elif self.path == "/silence":
            self.player.silence()
            self._send(200, {"ok": True})
        elif self.path == "/shutdown":
            self.player.silence()
            self._send(200, {"ok": True})
            # shutdown() blocks until serve_forever() returns: call it off-thread.
            threading.Thread(target=self.server.shutdown, daemon=True).start()
        else:
            self._send(404, {"error": "not found"})


def main():
    home = fc.CONFIG_DIR
    os.makedirs(home, exist_ok=True)

    token = secrets.token_hex(16)
    _Handler.token = token
    _Handler.player = _Player()

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]

    with open(fc.config_path("daemon.state"), "w", encoding="utf-8") as f:
        json.dump({"port": port, "token": token}, f)

    _Player._log("daemon started on port %d (pid %d)" % (port, os.getpid()))

    def shutdown(signum, frame):  # noqa: ARG001
        _Handler.player.silence()
        try:
            os.unlink(fc.config_path("daemon.state"))
        except OSError:
            pass
        sys.exit(0)

    try:
        import signal
        signal.signal(signal.SIGTERM, shutdown)
        signal.signal(signal.SIGINT, shutdown)
    except (ImportError, ValueError):
        pass

    server.serve_forever()
    server.server_close()
    try:
        os.unlink(fc.config_path("daemon.state"))
    except OSError:
        pass
    _Player._log("daemon stopped (pid %d)" % os.getpid())


if __name__ == "__main__":
    main()
