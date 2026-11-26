#!/usr/bin/env python3
"""Unit tests for Franco's pure logic: sanitiser, <spoken> extraction, voice
mapping, wake-word pattern, and Stop-hook transcript parsing.

Run: python tests/test_franco.py
No audio, no network, no daemon required.
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hooks"))

import franco_common as fc  # noqa: E402
import prompt_hook as ph  # noqa: E402
import stop_hook as sh  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail))


# --- sanitiser ----------------------------------------------------------------
check("sanitise strips code fences", "```py\ncode()\n```" not in fc.sanitise("a ```py\ncode()\n``` b"))
check("sanitise strips bold", "**pippo**" not in fc.sanitise("ciao **pippo** come"))
check("sanitise strips inline code", "`ls -la`" not in fc.sanitise("run `ls -la` ora"))
check("sanitise unwraps links", fc.sanitise("see [docs](http://x) here") == "see docs here")
check("sanitise strips headers", fc.sanitise("## Titolo").startswith("Titolo"))
check("sanitise collapses whitespace", fc.sanitise("a\n\n  b   c") == "a. b c")
check("sanitise empty", fc.sanitise("") == "")

# --- spoken extraction ----------------------------------------------------------
lang, text = fc.extract_spoken('Blah <spoken lang="it">Fatto, tutto ok.</spoken>')
check("extract it tag", (lang, text) == ("it", "Fatto, tutto ok."))
lang, text = fc.extract_spoken('x <spoken lang=\'en\'>Done.</spoken>')
check("extract en single quotes", (lang, text) == ("en", "Done."))
lang, text = fc.extract_spoken("no tag here")
check("no tag", (lang, text) == (None, None))
lang, text = fc.extract_spoken('<spoken lang="en">one</spoken> mid <spoken lang="it">due</spoken>')
check("last tag wins", (lang, text) == ("it", "due"))
lang, text = fc.extract_spoken('<spoken lang="IT-IT">Ciao.</spoken>')
check("lang lowercased", lang == "it-it")

# --- voice mapping ----------------------------------------------------------------
vm = dict(fc.DEFAULT_VOICE_MAP)
check("voice it", fc.voice_for_lang("it", vm) == "it-IT-ElsaNeural")
check("voice it-IT", fc.voice_for_lang("it-IT", vm) == "it-IT-ElsaNeural")
check("voice en-US", fc.voice_for_lang("en-US", vm) == "en-US-AvaMultilingualNeural")
check("voice unknown falls to default", fc.voice_for_lang("xx", vm) == vm["default"])
check("voice empty falls to default", fc.voice_for_lang("", vm) == vm["default"])

# --- wake word pattern ---------------------------------------------------------------
ph.CONNECTORS = r"comunque|btw|anyway"  # freeze for tests
pattern = ph.wake_pattern("franco")
m = pattern.match("Comunque Franco, domani ho una riunione alle 3")
check("wake 'Comunque Franco,'", m and m.group(1).strip() == "domani ho una riunione alle 3")
m = pattern.match("comunque FRANCO prova")
check("wake lowercase caps mix", m and m.group(1).strip() == "prova")
m = pattern.match("btw franco nota a margine")
check("wake english connector", m and m.group(1).strip() == "nota a margine")
check("wake no match plain", pattern.match("fix the bug in parser.py") is None)
check("wake no match wake only", pattern.match("Comunque Franco") is None or pattern.match("Comunque Franco").group(1).strip() == "")
other = ph.wake_pattern("alfredo")
m = other.match("Comunque Alfredo, ricordati la scadenza")
check("wake custom name", m and m.group(1).strip() == "ricordati la scadenza")
check("wake other name no cross-match", pattern.match("Comunque Alfredo, x") is None)

# --- stop hook transcript parsing -------------------------------------------------------
with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
    json.dump({"type": "user", "message": {"role": "user", "content": "ciao"}}, f)
    f.write("\n")
    json.dump({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "Analizzo il file. <spoken lang=\"it\">Ho trovato il bug, correggo ora.</spoken>"}
    ]}}, f)
    f.write("\n")
    json.dump({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "t1", "name": "Edit", "input": {}}
    ]}}, f)
    f.write("\n")
    transcript = f.name
text = sh.last_assistant_text(transcript, attempts=1)
check("transcript last text msg", 'Ho trovato il bug' in text)
lang, summary = fc.extract_spoken(text)
check("transcript spoken extracted", (lang, summary) == ("it", "Ho trovato il bug, correggo ora."))
os.unlink(transcript)

# A previous turn's summary must never be replayed for the current turn.
with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
    for entry in (
        {"type": "user", "message": {"role": "user", "content": "primo"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": '<spoken lang="it">Vecchio.</spoken>'}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "secondo"}]}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t2", "name": "Read", "input": {}}]}},
        {"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": "x"}]}},
    ):
        f.write(json.dumps(entry) + "\n")
    transcript = f.name
check("transcript ignores previous turn", sh.last_assistant_text(transcript, attempts=1) == "")
os.unlink(transcript)

check("stop text prefers last_assistant_message",
      sh.turn_text({"last_assistant_message": 'ok <spoken lang="en">Done.</spoken>',
                    "transcript_path": "/nonexistent"}) == 'ok <spoken lang="en">Done.</spoken>')
check("stop text without message or transcript is empty", sh.turn_text({}) == "")

# --- plugin packaging --------------------------------------------------------------------
with open(os.path.join(ROOT, "hooks", "hooks.json"), encoding="utf-8") as f:
    hooks_cfg = json.load(f)
events = hooks_cfg.get("hooks") or {}
check("hooks.json has 'hooks' wrapper",
      set(events) == {"SessionStart", "UserPromptSubmit", "Stop", "SessionEnd"}, str(list(hooks_cfg)))
commands = [h["command"] for ev in events.values() for m in ev for h in m["hooks"]]
check("hooks run through the launcher",
      commands and all('/hooks/run.sh" --hook ' in c for c in commands), str(commands))
with open(os.path.join(ROOT, "requirements.txt"), encoding="utf-8") as f:
    reqs = f.read()
check("requirements pins the tested edge-tts range", fc.EDGE_TTS_SPEC in reqs)

# --- interpreter and daemon start-up -------------------------------------------------------
import contextlib  # noqa: E402
import io  # noqa: E402
import subprocess  # noqa: E402

import session_start as ss  # noqa: E402

work = tempfile.mkdtemp(prefix="franco_test_")
fc.CONFIG_DIR = work

if os.name == "nt":
    fake_env = os.path.join(work, "env")
    os.makedirs(fake_env)
    for exe in ("python.exe", "pythonw.exe"):
        open(os.path.join(fake_env, exe), "w").close()
    real_exe = sys.executable
    sys.executable = os.path.join(fake_env, "python.exe")
    check("daemon uses pythonw of the hook interpreter",
          fc.daemon_python() == os.path.join(fake_env, "pythonw.exe"), fc.daemon_python())
    os.unlink(os.path.join(fake_env, "pythonw.exe"))
    check("daemon falls back to the hook interpreter", fc.daemon_python() == sys.executable)
    sys.executable = real_exe
else:
    check("daemon uses the hook interpreter", fc.daemon_python() == sys.executable)

real_popen, real_healthy = subprocess.Popen, fc.daemon_healthy


def _no_python(*args, **kwargs):
    raise FileNotFoundError("pythonw not found")


subprocess.Popen, fc.daemon_healthy = _no_python, (lambda timeout=0.5: False)
try:
    started = fc.ensure_daemon(wait_seconds=0.1)
except OSError as exc:
    started = "raised %r" % exc
subprocess.Popen, fc.daemon_healthy = real_popen, real_healthy
check("ensure_daemon reports a failed launch", started is False, str(started))
with open(fc.config_path("daemon.log"), encoding="utf-8") as f:
    check("failed launch is logged", "pythonw not found" in f.read())


def run_session_start(edge_ok, daemon_ok):
    saved = (fc.is_enabled, fc.edge_tts_available, fc.ensure_daemon, fc.read_stdin_json)
    fc.is_enabled = lambda: True
    fc.edge_tts_available = lambda: edge_ok
    fc.ensure_daemon = lambda wait_seconds=3.0: daemon_ok
    fc.read_stdin_json = lambda: {}
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out):
            ss.main()
    finally:
        fc.is_enabled, fc.edge_tts_available, fc.ensure_daemon, fc.read_stdin_json = saved
    return json.loads(out.getvalue() or "{}")


res = run_session_start(edge_ok=False, daemon_ok=True)
check("session start flags missing edge-tts",
      "pip install" in res.get("systemMessage", "") and "hookSpecificOutput" not in res, str(res))
res = run_session_start(edge_ok=True, daemon_ok=False)
check("session start flags a daemon that did not start",
      "daemon.log" in res.get("systemMessage", "") and "hookSpecificOutput" not in res, str(res))
res = run_session_start(edge_ok=True, daemon_ok=True)
check("session start injects the spoken rule",
      "<spoken" in res.get("hookSpecificOutput", {}).get("additionalContext", "")
      and "systemMessage" not in res, str(res))

# Hook stdin is UTF-8 JSON even when Windows' code page is not.
env = dict(os.environ, PYTHONUTF8="0", PYTHONIOENCODING="")
probe = subprocess.run(
    [sys.executable, "-c", "import franco_common as fc; print(ascii(fc.read_stdin_json()))"],
    input=json.dumps({"prompt": "perché sì"}, ensure_ascii=False).encode("utf-8"),
    capture_output=True, cwd=os.path.join(ROOT, "hooks"), env=env,
)
check("hook stdin decoded as UTF-8", "perch\\xe9 s\\xec" in probe.stdout.decode(), probe.stdout + probe.stderr)

# --- launcher (hooks/run.sh) ----------------------------------------------------------------


def find_bash():
    if os.name != "nt":
        return "/bin/bash" if os.path.exists("/bin/bash") else None
    explicit = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if explicit and os.path.exists(explicit):
        return explicit
    git = __import__("shutil").which("git")  # Git Bash, never WSL's bash.exe
    if not git:
        return None
    # git.exe lives in <Git>\cmd, <Git>\bin or <Git>\mingw64\bin: walk up to <Git>.
    base = os.path.dirname(git)
    for _ in range(3):
        for rel in (("bin", "bash.exe"), ("usr", "bin", "bash.exe")):
            cand = os.path.join(base, *rel)
            if os.path.exists(cand):
                return cand
        base = os.path.dirname(base)
    return None


BASH = find_bash()
RUN_SH = os.path.join(ROOT, "hooks", "run.sh").replace("\\", "/")


def run_sh(args, home, extra_env=None, stdin=b""):
    env = dict(os.environ, FRANCO_HOME=home)
    env.pop("FRANCO_PYTHON", None)
    env.update(extra_env or {})
    return subprocess.run([BASH, RUN_SH] + args, input=stdin, capture_output=True, env=env, timeout=30)


if BASH is None:
    print("  --  launcher tests skipped (Git Bash not found)")
else:
    home = tempfile.mkdtemp(prefix="franco_home_")
    r = run_sh(["--hook", "session_start.py"], home)
    check("launcher: hook is a no-op while speech is off",
          r.returncode == 0 and r.stdout == b"", r.stdout + r.stderr)

    r = run_sh(["franco_ctl.py", "status"], home, {"FRANCO_PYTHON": sys.executable})
    out = r.stdout.decode("utf-8", "replace")
    check("launcher: FRANCO_PYTHON is honoured",
          r.returncode == 0 and "python: " + sys.executable in out, out + r.stderr.decode())

    r = run_sh(["franco_ctl.py", "status"], home, {"FRANCO_PYTHON": os.path.join(home, "nope.exe")})
    check("launcher: broken FRANCO_PYTHON fails clearly",
          r.returncode == 127 and b"Python 3.10+" in r.stderr, r.stderr)

    stubs = os.path.join(home, "stubs")
    os.makedirs(stubs)
    for name in ("python", "python3"):  # mimic the Microsoft Store aliases
        path = os.path.join(stubs, name)
        with open(path, "w", newline="\n") as f:
            f.write("#!/bin/sh\necho 'Python was not found; run without arguments to install'\nexit 49\n")
        os.chmod(path, 0o755)
    open(os.path.join(home, "enabled"), "w").close()
    r = run_sh(["--hook", "session_start.py"], home, {"PATH": stubs})
    msg = json.loads(r.stdout.decode() or "{}").get("systemMessage", "")
    check("launcher: Store stubs are rejected with a clear message",
          r.returncode == 0 and "no working Python 3.10+" in msg, r.stdout + r.stderr)
    check("launcher: rejected stub is not cached", not os.path.exists(os.path.join(home, "python")))
    __import__("shutil").rmtree(home, ignore_errors=True)

__import__("shutil").rmtree(work, ignore_errors=True)

print()
if FAILURES:
    print("%d FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all tests passed")
