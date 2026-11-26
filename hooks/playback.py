"""Audio playback backends for the Franco daemon.

Backends (selected by FRANCO_PLAYBACK env var, else auto-detect):
  mci   Windows Media Control Interface via winmm.dll (mp3 capable)
  afplay macOS (v2 — reserved)
  null  no audio; verifies the file exists and pretends to play (tests)

The synth step (edge-tts) is cross-platform; only this module is
platform-specific, so adding a backend here is all that v2 needs.
"""

import os
import threading
import time


def get_backend():
    forced = os.environ.get("FRANCO_PLAYBACK", "").strip().lower()
    if forced in ("mci", "null", "afplay"):
        return forced
    if os.name == "nt":
        return "mci"
    if os.uname().sysname == "Darwin":  # pragma: no cover
        return "afplay"
    return "null"


def play(path, stop_event):
    """Play an audio file, returning early if stop_event is set.

    Blocks until playback finishes or stop_event fires. Returns True if the
    file was played to completion.
    """
    backend = get_backend()
    if backend == "mci":
        return _play_mci(path, stop_event)
    if backend == "null":
        # Fake a duration so queue/interrupt logic is exercised in tests.
        size = os.path.getsize(path) if os.path.exists(path) else 0
        deadline = time.monotonic() + min(2.0, 0.05 + size / 50000)
        while not stop_event.is_set() and time.monotonic() < deadline:
            time.sleep(0.05)
        return not stop_event.is_set()
    return False  # pragma: no cover — afplay arrives in v2


# --- MCI (Windows) ------------------------------------------------------------

_MCI_PLAY_POLL = 0.08


def _play_mci(path, stop_event):
    import ctypes

    winmm = ctypes.WinDLL("winmm.dll")
    winmm.mciSendStringW.argtypes = [ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint, ctypes.c_void_p]
    winmm.mciSendStringW.restype = ctypes.c_uint

    alias = "franco_audio"
    buf = ctypes.create_unicode_buffer(128)

    def send(cmd):
        return winmm.mciSendStringW(cmd, buf, 128, None)

    cmd_open = 'open "{}" type mpegvideo alias {}'.format(path, alias)
    if send(cmd_open) != 0:
        # Some builds need the plain filename form.
        if send('open "{}" alias {}'.format(path, alias)) != 0:
            return False
    try:
        if send("play {} from 0".format(alias)) != 0:
            return False
        while not stop_event.is_set():
            if send("status {} mode".format(alias)) != 0:
                return False
            mode = buf.value.lower()
            if mode in ("stopped", "", "not ready"):
                break
            time.sleep(_MCI_PLAY_POLL)
        completed = False
        if send("status {} mode".format(alias)) == 0:
            completed = buf.value.lower() == "stopped"
        return completed and not stop_event.is_set()
    finally:
        send("stop {}".format(alias))
        send("close {}".format(alias))
