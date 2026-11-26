#!/usr/bin/env python3
"""SessionStart hook: inject the <spoken> emission rule when speech is on,
and make sure the daemon is running (warm, so replies speak with no cold start).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402

SPOKEN_RULE = (
    "FRANCO SPEECH IS ACTIVE in this session. End every CONVERSATIONAL reply "
    "with a <spoken lang=\"xx\"> tag containing 1-2 sentences of plain prose "
    "that summarize what you just said or did for someone listening instead of "
    "reading — no markdown, no lists, no code, no commands, no long numbers. "
    "Write the tag in the same language as your reply and set lang accordingly "
    "(e.g. lang=\"it\" for Italian, lang=\"en\" for English). Replies that are "
    "data-shaped (mostly code, tables, diffs, file dumps) get NO tag at all. "
    "The tag content is read aloud verbatim. Do not mention the tag to the user."
)


def read_stdin_json():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return {}


def main():
    if not fc.is_enabled():
        return
    read_stdin_json()  # consumed for symmetry; source is not used today
    healthy = fc.ensure_daemon()
    if not healthy:
        # Session still proceeds; speech will be skipped this session.
        return
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": SPOKEN_RULE,
        }
    }))


if __name__ == "__main__":
    main()
    sys.exit(0)
