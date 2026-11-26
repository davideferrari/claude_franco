"""Shared helpers for the Franco plugin hooks and daemon.

Config lives in ~/.franco/ (override with FRANCO_HOME env var, used by tests):
  enabled        presence of this file = speech on
  wakeword       text file holding the wake name (default: franco)
  voice_map.json {"it": "...", "en": "...", "default": "..."}
  daemon.state   {"port": int, "token": str} written by the daemon
  daemon.log     daemon log
  python         interpreter chosen by hooks/run.sh (cache; safe to delete)
"""

import json
import os
import re
import sys
import urllib.error
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

# Tested range; keep in sync with requirements.txt (a unit test checks it).
EDGE_TTS_SPEC = "edge-tts>=7.0,<8"


def config_path(name):
    return os.path.join(CONFIG_DIR, name)


def read_stdin_json():
    """Parse the hook payload. Claude Code sends UTF-8 JSON; decode it as such
    instead of trusting the console code page (cp1252 on most Windows setups)."""
    try:
        raw = sys.stdin.buffer.read().decode("utf-8", "replace")
        data = json.loads(raw) if raw.strip() else {}
        return data if isinstance(data, dict) else {}
    except (ValueError, OSError, AttributeError):
        return {}


def log(msg):
    """Append a line to daemon.log; never raises."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(config_path("daemon.log"), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def edge_tts_available():
    import importlib.util

    return importlib.util.find_spec("edge_tts") is not None


def edge_tts_version():
    try:
        from importlib.metadata import version

        return version("edge-tts")
    except Exception:  # noqa: BLE001 — metadata lookups vary across installs
        return None


def install_hint():
    """Exact command that installs the dependency into the running interpreter."""
    return '"%s" -m pip install "%s"' % (sys.executable, EDGE_TTS_SPEC)


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
    r"<spoken(?:\s+lang\s*=\s*[\"']?([A-Za-z0-9-]*)[\"']?)?\s*>(.*?)</spoken\s*>",
    re.DOTALL | re.IGNORECASE,
)

# Code is removed before looking for the tag: a tag shown as an example in a
# code block or inline code span is not an instruction to speak.
_FENCED_RE = re.compile(r"^[ \t]*(```|~~~)[^\n]*\n.*?^[ \t]*\1[^\n]*$", re.DOTALL | re.MULTILINE)
_OPEN_FENCE_RE = re.compile(r"^[ \t]*(```|~~~).*\Z", re.DOTALL | re.MULTILINE)
_INLINE_CODE_RE = re.compile(r"(`+)[^\n]*?\1")

# A summary is read aloud as-is, so anything that is not plain prose is refused.
MAX_SPOKEN_LEN = 800
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)
_MARKUP_RE = re.compile(r"<\s*/?\s*[A-Za-z!]")


def code_spans(text):
    """(start, end) ranges of fenced blocks (an unclosed fence runs to the end)
    and inline code spans."""
    spans = [m.span() for m in _FENCED_RE.finditer(text)]

    def outside(pos):
        return not any(a <= pos < b for a, b in spans)

    for m in _OPEN_FENCE_RE.finditer(text):
        if outside(m.start()):
            spans.append(m.span())
            break
    spans += [m.span() for m in _INLINE_CODE_RE.finditer(text) if outside(m.start())]
    return spans


def extract_spoken(text):
    """Return (lang, summary) from the last <spoken> tag outside code, or (None, None).

    A tag that starts inside a code block or span is an example, not an
    instruction. Code *inside* a real tag is kept, so the summary is then
    refused by unspeakable_reason() instead of being read with gaps.
    lang is "" when the tag has no lang attribute (the default voice is used)."""
    text = text or ""
    spans = code_spans(text)
    matches = [
        m for m in SPOKEN_RE.finditer(text)
        if not any(a <= m.start() < b for a, b in spans)
    ]
    if not matches:
        return None, None
    lang, summary = matches[-1].groups()
    return (lang or "").lower(), summary.strip()


def unspeakable_reason(summary):
    """Why a summary must not be read aloud, or None if it is plain prose."""
    if len(summary) > MAX_SPOKEN_LEN:
        return "too long"
    if "`" in summary or "~~~" in summary:
        return "code"
    if _TABLE_ROW_RE.search(summary):
        return "table"
    if _MARKUP_RE.search(summary):
        return "markup"
    return None


# --- sanitiser ---------------------------------------------------------------

_MD_NOISE = [
    (re.compile(r"```.*?```", re.DOTALL), " "),
    (re.compile(r"(`+)[^\n]*?\1"), " "),
    (re.compile(r"!\[.*?\]\(.*?\)", re.DOTALL), " "),
    (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),
    (re.compile(r"^#{1,6}\s*", re.MULTILINE), ""),
    (re.compile(r"(\*\*|__|~~)"), ""),
    (re.compile(r"^\s*[-*+]\s+", re.MULTILINE), ""),
    (re.compile(r"^\s*\d+\.\s+", re.MULTILINE), ""),
    (re.compile(r"^\s*\|.*$", re.MULTILINE), ""),
    (re.compile(r"\|"), " "),
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"\n{2,}"), ". "),
]


def sanitise(text):
    """Remove formatting before synthesis. Code and table rows are dropped, not
    read. This is formatting cleanup, not a filter for secrets."""
    out = text or ""
    for pattern, repl in _MD_NOISE:
        out = pattern.sub(repl, out)
    out = re.sub(r"\s+", " ", out).strip()
    return "" if re.fullmatch(r"[\s.]*", out) else out


# --- daemon IPC --------------------------------------------------------------

def read_daemon_state():
    """The daemon's {"port", "token", "pid"}, or None if missing or malformed."""
    try:
        with open(config_path("daemon.state"), "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(state, dict):
        return None
    port, token = state.get("port"), state.get("token")
    if not isinstance(port, int) or isinstance(port, bool) or not 0 < port < 65536:
        return None
    if not isinstance(token, str) or not token:
        return None
    return state


def write_state(state):
    """Write daemon.state atomically (readers never see a half-written file)."""
    import time

    path = config_path("daemon.state")
    tmp = "%s.%d.tmp" % (path, os.getpid())
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    if os.name != "nt":
        os.chmod(tmp, 0o600)
    for attempt in range(10):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: a reader has the file open right now
            if attempt == 9:
                raise
            time.sleep(0.05)


def daemon_health(timeout=0.5):
    """The daemon's /health payload, or None if it is not reachable.

    The pid must match the state file, so a stale port reused by another
    process is not mistaken for the daemon."""
    state = read_daemon_state()
    if not state:
        return None
    try:
        with urllib.request.urlopen(
            "http://127.0.0.1:%d/health" % state["port"], timeout=timeout
        ) as resp:
            data = json.loads(resp.read().decode("utf-8") or "{}")
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("ok") is not True:
        return None
    if "pid" in state and data.get("pid") != state["pid"]:
        return None
    return data


def daemon_healthy(timeout=0.5):
    return daemon_health(timeout) is not None


def daemon_python():
    """Interpreter for the daemon: the same environment that runs the hooks,
    so edge-tts is found where it was installed. On Windows, prefer the
    windowless pythonw.exe that sits next to python.exe."""
    exe = sys.executable or "python"
    if os.name == "nt":
        windowless = os.path.join(os.path.dirname(exe), "pythonw.exe")
        if os.path.isfile(windowless):
            return windowless
    return exe


_BUILD_FILES = ("franco_common.py", "franco_daemon.py", "playback.py")
_build_id = None


def build_id():
    """Fingerprint of the daemon's code. A daemon reporting a different one in
    /health is running an older copy of the plugin and gets replaced."""
    global _build_id
    if _build_id is None:
        import hashlib

        here = os.path.dirname(os.path.abspath(__file__))
        digest = hashlib.sha256()
        for name in _BUILD_FILES:
            try:
                with open(os.path.join(here, name), "rb") as f:
                    digest.update(f.read())
            except OSError:
                digest.update(name.encode("utf-8"))
        _build_id = digest.hexdigest()[:12]
    return _build_id


def _is_current(health):
    return health is not None and health.get("build") == build_id()


def ensure_daemon(wait_seconds=3.0):
    """Start the daemon detached unless a healthy one running this code exists.
    Returns True once a current daemon answers."""
    import subprocess
    import time

    health = daemon_health()
    if _is_current(health):
        return True
    if health is not None:
        log("replacing daemon build %s with %s" % (health.get("build", "unknown"), build_id()))
        post_to_daemon("/shutdown", {}, timeout=1.0)
        deadline = time.monotonic() + 2.0
        while daemon_health(0.3) is not None and time.monotonic() < deadline:
            time.sleep(0.1)

    here = os.path.dirname(os.path.abspath(__file__))
    cmd = [daemon_python(), os.path.join(here, "franco_daemon.py")]
    kwargs = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.name == "nt":
        kwargs["creationflags"] = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        log("daemon launch failed (%s): %s" % (cmd[0], exc))
        return False

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        time.sleep(0.25)
        if _is_current(daemon_health(0.3)):
            return True
    log("daemon did not answer /health within %.1fs (%s)" % (wait_seconds, cmd[0]))
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
