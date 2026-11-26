#!/usr/bin/env bash
# Franco launcher: finds a working Python 3.10+ and runs one of Franco's scripts.
#
#   run.sh --hook <script.py>    hook mode: returns at once while speech is off
#                                and never makes the Claude Code session fail
#   run.sh <script.py> [args]    CLI mode, used by /franco and the franco skill
#
# Interpreter lookup, first working one wins:
#   1. $FRANCO_PYTHON            explicit choice; if it is broken, nothing else is tried
#   2. <config>/python           the interpreter found on a previous run
#   3. py -3, python3, python    the Windows launcher first, then the usual names
# Every candidate is probed, so the Microsoft Store "app execution alias" stubs
# (which only print "Python was not found") are skipped.
#
# Only bash builtins are used, so this works with a minimal PATH.

hook=0
if [ "$1" = "--hook" ]; then
  hook=1
  shift
fi
script="$1"
shift

here="${BASH_SOURCE[0]%/*}"
[ "$here" = "${BASH_SOURCE[0]}" ] && here=.
home="${FRANCO_HOME:-${USERPROFILE:-$HOME}/.franco}"

# Speech off: hooks have nothing to do, so do not even start Python.
if [ "$hook" = 1 ] && [ ! -e "$home/enabled" ]; then
  exit 0
fi

# Hook stdin/stdout carry UTF-8 JSON whatever the Windows code page is.
export PYTHONUTF8=1

probe='import sys; sys.exit(1) if sys.version_info < (3, 10) else print(sys.executable.replace(chr(92), "/"))'

resolve() {
  local out cached
  if [ -n "$FRANCO_PYTHON" ]; then
    out=$("$FRANCO_PYTHON" -c "$probe" </dev/null 2>/dev/null) && [ -n "$out" ] || return 1
    printf '%s' "$out"
    return 0
  fi
  if [ -r "$home/python" ]; then
    IFS= read -r cached <"$home/python"
    if [ -n "$cached" ] && [ -f "$cached" ]; then
      printf '%s' "$cached"
      return 0
    fi
  fi
  out=$(py -3 -c "$probe" </dev/null 2>/dev/null) ||
    out=$(python3 -c "$probe" </dev/null 2>/dev/null) ||
    out=$(python -c "$probe" </dev/null 2>/dev/null) ||
    return 1
  [ -n "$out" ] || return 1
  [ -d "$home" ] && printf '%s\n' "$out" >"$home/python" 2>/dev/null
  printf '%s' "$out"
}

py=$(resolve)
if [ -z "$py" ]; then
  hint="no working Python 3.10+ found (tried FRANCO_PYTHON, py -3, python3, python). Install Python from python.org or set FRANCO_PYTHON to the interpreter to use."
  if [ "$hook" = 1 ]; then
    # Report once per session, at start-up; the other hooks stay silent.
    if [ "$script" = "session_start.py" ]; then
      printf '{"systemMessage": "Franco: speech is on, but %s"}\n' "$hint"
    fi
    exit 0
  fi
  printf 'franco: %s\n' "$hint" >&2
  exit 127
fi

if [ "$hook" = 1 ]; then
  "$py" "$here/$script" "$@"
  exit 0  # a failing hook must never break the Claude Code session
fi
exec "$py" "$here/$script" "$@"
