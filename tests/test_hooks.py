#!/usr/bin/env python3
"""Integration tests: each hook runs for real through hooks/run.sh, with a JSON
payload on stdin, an isolated FRANCO_HOME and a spy daemon that records what
it receives. Needs bash (Git Bash on Windows); skipped otherwise.

Run: python tests/test_hooks.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hooks"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import franco_common as fc  # noqa: E402
import franco_daemon as fd  # noqa: E402
from bash_finder import find_bash  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail))


class SpyPlayer:
    def __init__(self):
        self.said = []
        self.silenced = 0

    def say(self, text, lang, voice=None):
        self.said.append((text, lang))
        return 1

    def silence(self):
        self.silenced += 1

    def health(self):
        return {"ok": True, "pid": os.getpid(), "synth": True, "playback": True, "queue": 0}


BASH = find_bash()
RUN_SH = os.path.join(ROOT, "hooks", "run.sh").replace("\\", "/")


def hook(script, payload, home):
    env = dict(os.environ, FRANCO_HOME=home, FRANCO_PYTHON=sys.executable)
    raw = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    r = subprocess.run([BASH, RUN_SH, "--hook", script], input=raw, capture_output=True, env=env, timeout=30)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


if BASH is None:
    print("  --  hook integration tests skipped (bash not found)")
    sys.exit(0)

home = tempfile.mkdtemp(prefix="franco_hooks_")
fc.CONFIG_DIR = home
open(os.path.join(home, "enabled"), "w").close()

spy = SpyPlayer()
server = fd.make_server(spy, token="spy-token")
threading.Thread(target=server.serve_forever, daemon=True).start()
fc.write_state({"port": server.server_address[1], "token": "spy-token", "pid": os.getpid()})

# UserPromptSubmit: barge-in, plus the wake name with accented text intact.
before = spy.silenced
rc, out, err = hook("prompt_hook.py", {"prompt": "Comunque Franco, ricordati che c'è la demo perché è importante"}, home)
ctx = json.loads(out or "{}").get("hookSpecificOutput", {}).get("additionalContext", "")
check("prompt hook stops the audio", rc == 0 and spy.silenced == before + 1, err)
check("wake name note keeps accents", "ricordati che c'è la demo perché è importante" in ctx, out + err)
rc, out, err = hook("prompt_hook.py", {"prompt": "aggiungi un test per il parser"}, home)
check("ordinary prompt adds no context", rc == 0 and out.strip() == "", out)

# Stop: the turn's summary is delivered once, with its language.
turn = {"session_id": "s", "prompt_id": "p1",
        "last_assistant_message": 'Fatto.\n\n<spoken lang="it">Ho aggiornato i test, è tutto verde.</spoken>'}
rc, out, err = hook("stop_hook.py", turn, home)
check("stop hook delivers the summary",
      rc == 0 and spy.said == [("Ho aggiornato i test, è tutto verde.", "it")], "%r %s" % (spy.said, err))
hook("stop_hook.py", turn, home)
check("same turn is not spoken twice", len(spy.said) == 1, repr(spy.said))

code_turn = {"session_id": "s", "prompt_id": "p2",
             "last_assistant_message": 'Esempio:\n```\n<spoken lang="it">non leggere</spoken>\n```'}
hook("stop_hook.py", code_turn, home)
check("tag inside code is not spoken", len(spy.said) == 1, repr(spy.said))

bad_turn = {"session_id": "s", "prompt_id": "p3",
            "last_assistant_message": '<spoken lang="it">Esegui `rm -rf build` ora.</spoken>'}
hook("stop_hook.py", bad_turn, home)
with open(fc.config_path("daemon.log"), encoding="utf-8") as f:
    log_text = f.read()
check("summary with code is refused and logged",
      len(spy.said) == 1 and "summary skipped (code" in log_text and "rm -rf" not in log_text, log_text)

# Malformed input never breaks the session.
rc, out, err = hook("stop_hook.py", b"\xff not json", home)
check("malformed stdin is harmless", rc == 0 and out == "", out + err)

# SessionEnd silences.
before = spy.silenced
rc, out, err = hook("session_end.py", {"reason": "prompt_input_exit"}, home)
check("session end stops the audio", rc == 0 and spy.silenced == before + 1, err)

# Speech off: nothing reaches the daemon.
os.unlink(os.path.join(home, "enabled"))
said, silenced = len(spy.said), spy.silenced
hook("stop_hook.py", dict(turn, prompt_id="p9"), home)
hook("prompt_hook.py", {"prompt": "ciao"}, home)
check("speech off sends nothing", len(spy.said) == said and spy.silenced == silenced)

server.shutdown()
server.server_close()
shutil.rmtree(home, ignore_errors=True)

print()
if FAILURES:
    print("%d FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all tests passed")
