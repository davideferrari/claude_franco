#!/usr/bin/env python3
"""Tests for the Franco daemon: playback queue, interruption, error handling and
the local HTTP service. Synthesis and playback are simulated: no network, no audio.

Run: python tests/test_daemon.py
"""

import json
import os
import sys
import tempfile
import threading
import time
import types
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hooks"))

import franco_common as fc  # noqa: E402

WORK = tempfile.mkdtemp(prefix="franco_daemon_test_")
fc.CONFIG_DIR = WORK

import franco_daemon as fd  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail))


def wait_for(cond, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if cond():
            return True
        time.sleep(0.01)
    return cond()


class FakeAudio:
    """Synthesiser + player doubles. Each can be gated to hold the worker."""

    def __init__(self):
        self.synth_gate = threading.Event()
        self.synth_gate.set()
        self.play_gate = threading.Event()
        self.play_gate.set()
        self.synth_started = threading.Event()
        self.play_started = threading.Event()
        self.synth_error = None
        self.play_result = True
        self.played = []
        self.files = []
        self.voices = []

    def synthesise(self, text, voice):
        self.voices.append(voice)
        self.synth_started.set()
        self.synth_gate.wait(5)
        if self.synth_error:
            raise self.synth_error
        fd_, path = tempfile.mkstemp(prefix="franco_", suffix=".mp3", dir=WORK)
        os.write(fd_, b"ID3")
        os.close(fd_)
        self.files.append(path)
        return path

    def play(self, path, stop_event):
        self.play_started.set()
        while not self.play_gate.is_set():
            if stop_event.is_set():
                return False
            time.sleep(0.01)
        if stop_event.is_set():
            return False
        self.played.append(path)
        return self.play_result


def new_player(audio, **kw):
    return fd.Player(synthesise=audio.synthesise, play=audio.play, **kw)


def leftovers(audio):
    return [p for p in audio.files if os.path.exists(p)]


# --- queue and playback -------------------------------------------------------------------
audio = FakeAudio()
player = new_player(audio)
player.say("uno", "it")
check("say is played", wait_for(lambda: len(audio.played) == 1))
check("played file is removed", wait_for(lambda: not leftovers(audio)), str(leftovers(audio)))
check("voice comes from the language map", audio.voices == [fc.voice_for_lang("it")], str(audio.voices))
player.say("prova", "it", voice="it-IT-DiegoNeural")
check("an explicit voice overrides the map", wait_for(lambda: audio.voices[-1:] == ["it-IT-DiegoNeural"]),
      str(audio.voices))
player.close()

# Queue is bounded: with the worker held, only the newest MAX_QUEUE items survive.
audio = FakeAudio()
audio.synth_gate.clear()
player = new_player(audio, max_queue=3)
player.say("first", "it")
wait_for(audio.synth_started.is_set)
sizes = [player.say("item %d" % i, "it") for i in range(6)]
check("queue never exceeds its bound", max(sizes) <= 3 and player.health()["queue"] == 3, str(sizes))
check("oldest queued item is dropped", [item[0] for item in player._items] == ["item 3", "item 4", "item 5"],
      str(list(player._items)))
audio.synth_gate.set()
check("bounded queue drains", wait_for(lambda: len(audio.played) == 4), str(len(audio.played)))
player.close()

# Concurrent producers cannot push the queue past its bound.
audio = FakeAudio()
audio.synth_gate.clear()
player = new_player(audio, max_queue=3)
player.say("hold", "it")
wait_for(audio.synth_started.is_set)
threads = [threading.Thread(target=lambda: [player.say("x", "it") for _ in range(50)]) for _ in range(8)]
for t in threads:
    t.start()
for t in threads:
    t.join()
check("concurrent say keeps the bound", len(player._items) == 3, str(len(player._items)))
audio.synth_gate.set()
player.close()

# --- interruption ---------------------------------------------------------------------------
# During synthesis: the audio must not start once the synthesis completes.
audio = FakeAudio()
audio.synth_gate.clear()
player = new_player(audio)
player.say("long", "it")
wait_for(audio.synth_started.is_set)
player.say("queued", "it")
player.silence()
audio.synth_gate.set()
time.sleep(0.3)
check("silence during synthesis prevents playback", audio.played == [] and not audio.play_started.is_set())
check("silence clears the queue", player.health()["queue"] == 0)
check("interrupted synthesis leaves no file", wait_for(lambda: not leftovers(audio)), str(leftovers(audio)))
player.close()

# During playback.
audio = FakeAudio()
audio.play_gate.clear()
player = new_player(audio)
player.say("playing", "it")
wait_for(audio.play_started.is_set)
player.silence()
time.sleep(0.2)
audio.play_gate.set()
time.sleep(0.2)
check("silence during playback stops it", audio.played == [])
check("stopped playback leaves no file", wait_for(lambda: not leftovers(audio)), str(leftovers(audio)))
player.close()

# Handoff: an item queued before silence() must never play after it.
audio = FakeAudio()
for _ in range(30):
    audio.played.clear()
    player = new_player(audio)
    player.say("race", "it")
    player.silence()
    time.sleep(0.02)
    late = list(audio.played)
    player.close()
    # Either it was already played before silence() or it was dropped; it may not
    # start afterwards. A play that started after silence would show up later.
    time.sleep(0.02)
    if audio.played != late:
        break
check("no late playback after silence", audio.played == late, "%r vs %r" % (audio.played, late))

# --- errors and health -------------------------------------------------------------------------
audio = FakeAudio()
audio.synth_error = OSError("network unreachable")
player = new_player(audio)
player.say("fails", "it")
check("synthesis failure is reported in health", wait_for(lambda: player.health()["synth"] is False))
audio.synth_error = None
player.say("works", "it")
check("health recovers after a good synthesis",
      wait_for(lambda: player.health()["synth"] is True and len(audio.played) == 1))
audio.play_result = False
player.say("bad device", "it")
check("playback failure is reported in health", wait_for(lambda: player.health()["playback"] is False))
audio.play_result = True
player.say("good device", "it")
check("health recovers after a good playback", wait_for(lambda: player.health()["playback"] is True))
player.close()
with open(fc.config_path("daemon.log"), encoding="utf-8") as f:
    log_text = f.read()
check("errors are logged", "network unreachable" in log_text and "FAILED" in log_text)
check("spoken text is never logged", "bad device" not in log_text and "works" not in log_text)

# Real synthesiser wrapper: the temporary file is removed when edge-tts raises.
fake_edge = types.ModuleType("edge_tts")


class _Communicate:
    def __init__(self, text, voice, **kwargs):
        self.kwargs = kwargs

    async def save(self, path):
        with open(path, "wb") as f:
            f.write(b"partial")
        raise ConnectionError("dropped")


fake_edge.Communicate = _Communicate
saved_module = sys.modules.get("edge_tts")
sys.modules["edge_tts"] = fake_edge
saved_tempdir = tempfile.tempdir
tempfile.tempdir = os.path.join(WORK, "synth")
os.makedirs(tempfile.tempdir)
try:
    fd.synthesise_edge_tts("ciao", "it-IT-ElsaNeural")
    raised = False
except ConnectionError:
    raised = True
check("synthesis error propagates", raised)
check("failed synthesis leaves no temp file", os.listdir(tempfile.tempdir) == [], str(os.listdir(tempfile.tempdir)))
tempfile.tempdir = saved_tempdir
if saved_module is None:
    del sys.modules["edge_tts"]
else:
    sys.modules["edge_tts"] = saved_module

# --- HTTP service ---------------------------------------------------------------------------------
audio = FakeAudio()
player = new_player(audio)
server = fd.make_server(player, token="t0k3n")
port = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()


def request(path, body=None, token="t0k3n", method="POST", headers=None):
    data = body if isinstance(body, bytes) or body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data, method=method)
    if token is not None:
        req.add_header("X-Franco-Token", token)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as err:
        return err.code, json.loads(err.read() or b"{}")


status, body = request("/health", method="GET", token=None)
check("health is public", status == 200 and body.get("ok") is True and body.get("pid") == os.getpid(), str(body))
check("wrong token is rejected", request("/say", {"text": "x"}, token="nope")[0] == 403)
check("missing token is rejected", request("/say", {"text": "x"}, token=None)[0] == 403)
check("invalid JSON is rejected", request("/say", b"{not json")[0] == 400)
check("non-object JSON is rejected", request("/say", b"[1, 2]")[0] == 400)
check("non-string text is rejected", request("/say", {"text": 42})[0] == 400)
check("invalid lang is rejected", request("/say", {"text": "ok", "lang": "it\"><x"})[0] == 400)
check("invalid voice is rejected", request("/say", {"text": "ok", "voice": "../../x"})[0] == 400)
check("voice id is accepted", request("/say", {"text": "ok", "voice": "it-IT-DiegoNeural"})[0] == 200)
check("oversized body is rejected", request("/say", {"text": "x" * (fd.MAX_BODY + 10)})[0] == 413)
check("GET on a command is refused", request("/say", method="GET")[0] == 405)
check("unknown path is 404", request("/nope", {})[0] == 404)
status, body = request("/say", {"text": "Ciao **mondo**", "lang": "it"})
check("valid say is accepted", status == 200 and body.get("ok") is True, str(body))
check("valid say is played", wait_for(lambda: len(audio.played) == 2), str(len(audio.played)))
check("empty text is skipped", request("/say", {"text": "   "})[1].get("skipped") == "empty")
check("silence is accepted", request("/silence", {})[0] == 200)
server.shutdown()
server.server_close()
player.close()

# --- single instance and state file -----------------------------------------------------------------
lock_path = fc.config_path("daemon.lock")
first = fd.acquire_single_instance(lock_path)
second = fd.acquire_single_instance(lock_path)
check("first daemon takes the lock", first is not None)
check("second daemon is refused", second is None)
first.close()
third = fd.acquire_single_instance(lock_path)
check("lock is released with its holder", third is not None)
third.close()

fc.write_state({"port": 1234, "token": "abc", "pid": 99})
check("state round-trips", fc.read_daemon_state() == {"port": 1234, "token": "abc", "pid": 99})
check("no temporary state file is left", [n for n in os.listdir(WORK) if n.startswith("daemon.state.")] == [])
with open(fc.config_path("daemon.state"), "w", encoding="utf-8") as f:
    f.write('["not", "a", "dict"]')
check("malformed state is ignored", fc.read_daemon_state() is None)
with open(fc.config_path("daemon.state"), "w", encoding="utf-8") as f:
    f.write('{"port": "80", "token": 5}')
check("mistyped state is ignored", fc.read_daemon_state() is None)

__import__("shutil").rmtree(WORK, ignore_errors=True)

print()
if FAILURES:
    print("%d FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all tests passed")
