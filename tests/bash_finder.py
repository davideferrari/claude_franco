"""Locate the bash that Claude Code uses for hooks: Git Bash on Windows, never
WSL's bash.exe from System32."""

import os
import shutil


def find_bash():
    if os.name != "nt":
        return shutil.which("bash")
    explicit = os.environ.get("CLAUDE_CODE_GIT_BASH_PATH")
    if explicit and os.path.exists(explicit):
        return explicit
    git = shutil.which("git")
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
