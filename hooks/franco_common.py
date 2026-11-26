"""Shared helpers for the Franco plugin hooks and daemon.

Config lives in ~/.franco/ (override with FRANCO_HOME env var, used by tests):
  enabled        presence of this file = speech on
  wakeword       text file holding the wake name (default: franco)
  voice_map.json {"it": "...", "en": "...", "default": "..."}
  daemon.state   {"port": int, "token": str} written by the daemon
  daemon.log     daemon log
"""

import json
import os
import re
import sys
import urllib.request

CONFIG_DIR = os.environ.get("FRANCO_HOME") or os.path.join(
    os.path.expanduser("~"), ".franco"
)

DEFAULT_VOICE_MAP = {
    "it": "it-IT-ElsaNeural",
    "en": "en-US-AvaMultilingualNeural",
    "default": "en-US-AvaMultilingualNeural",
}

MAX_TEXT_LEN = 4000


def config_path(name):
    return os.path.join(CONFIG_DIR, name)


def is_enabled():
    return os.path.exists(config_path("enabled"))


def read_wakeword():
    try:
        with open(config_path("wakeword"), "r", encoding="utf-8") as f:
            word = f.read().strip()
            if word:
                return word
    except OSError:
        pass
    return "franco"


def load_voice_map():
    try:
        with open(config_path("voice_map.json"), "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and data:
                return data
    except (OSError, ValueError):
        pass
    return dict(DEFAULT_VOICE_MAP)


def voice_for_lang(lang, voice_map=None):
    """Map a BCP-47 tag ('it', 'it-IT', 'en-US') to a voice id."""
    vm = voice_map or load_voice_map()
    lang = (lang or "").strip().lower()
    if not lang:
        return vm.get("default", DEFAULT_VOICE_MAP["default"])
    if lang in vm:
        return vm[lang]
    primary = lang.split("-")[0]
    if primary in vm:
        return vm[primary]
    return vm.get("default", DEFAULT_VOICE_MAP["default"])


# --- spoken tag extraction ---------------------------------------------------

SPOKEN_RE = re.compile(
    r"<spoken\s+lang=[\"']?([A-Za-z0-9-]+)[\"']?\s*>(.*?)</spoken\s*>",
    re.DOTALL | re.IGNORECASE,
)


def extract_spoken(text):
    """Return (lang, summary) from the last <spoken> tag in text, or (None, None)."""
    matches = SPOKEN_RE.findall(text or "")
    if not matches:
        return None, None
    lang, summary = matches[-1]
    return lang.lower(), summary.strip()


# --- sanitiser ---------------------------------------------------------------

_MD_NOISE = [
    (re.compile(r"```.*?```", re.DOTALL), " "),
    (re.compile(r"`([^`]*)`", re.DOTALL), r"\1"),
    (re.compile(r"!\[.*?\]\(.*?\)", re.DOTALL), " "),
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),
    (re.compile(r"^#{1,6}\s*", re.MULTILINE), ""),
    (re.compile(r"(\*\*|__|~~)"), ""),
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),
    (re.compile(r"^\s*\d+\.\s+", re.MULTILINE), ""),
    (re.compile(r"\|"), " "),
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"\n{2,}"), ". "),
]


def sanitise(text):
    """Last-resort cleanup of spoken text (the <spoken> tag should already be clean)."""
    out = text or ""
    for pattern, repl in _MD_NOISE:
        out = pattern.sub(repl, out)
    return re.sub(r"\s+", " ", out).strip()


# --- daemon IPC --------------------------------------------------------------

def read_daemon_state():
    try:
        with open(config_path("daemon.state"), "r", encoding="utf-8") as f:
            state = json.load(f)
        if isinstance(state, dict) and state.get("port") and state.get("token"):
            return state
    except (OSError, ValueError):
        pass
    return None


def daemon_healthy(timeout=0.5):
    state = read_daemon_state()
    if not state:
        return False
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:%d/health" % state["port"], timeout=timeout
        ) as resp:
            return resp.status == 200
    except (OSError, urllib.error.URLError):
        return False


def ensure_daemon(wait_seconds=3.0):
    """Start the daemon detached if it is not already healthy. Returns True if healthy."""
    if daemon_healthy():
        return True
    import subprocess

    here = os.path.dirname(os.path.abspath(__file__))
    daemon_py = os.path.join(here, "franco_daemon.py")
    if os.name == "nt":
        pythonw = "pythonw"
        creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        subprocess.Popen(
            [pythonw, daemon_py],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    else:
        subprocess.Popen(
            [sys.executable, daemon_py],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    import time

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        time.sleep(0.25)
        if daemon_healthy(0.3):
            return True
    return False


def post_to_daemon(path, payload, timeout=3.0):
    """Fire-and-forget POST to the daemon. Returns True if delivered."""
    state = read_daemon_state()
    if not state:
        return False
    url = "http://127.0.0.1:%d%s" % (state["port"], path)
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Franco-Token": state["token"],
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except (OSError, urllib.error.URLError, urllib.error.HTTPError):
        return False
