#!/usr/bin/env python3
"""UserPromptSubmit hook: barge-in + wake word ("Comunque Franco, ...").

1. Barge-in: whenever the user submits a prompt, stop the current playback.
   The user taking the floor is the interruption — no hotkey needed.
2. Wake word: if the prompt matches "<connector> <wake>, <rest>" (e.g.
   "Comunque Franco, domani ho una riunione"), inject context telling Claude
   to treat the rest as a mid-task aside: acknowledge aloud in one line,
   keep working.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402

CONNECTORS = r"comunque|a proposito|fra l'altro|btw|anyway|by the way"

BTW_CONTEXT = (
    "FRANCO ASIDE DETECTED: the user submitted a mid-task aside "
    "(pattern: '<connector> {wake}, <phrase>'). The verbatim prompt text is: "
    "\"{prompt}\". Treat the phrase after the wake word as a NOTE, not a new "
    "task: do NOT stop, undo, or redirect whatever you were doing. If you are "
    "still mid-task, keep working after this. Acknowledge the note in ONE "
    "short conversational line and append a <spoken lang=\"...\"> tag with "
    "that line (plain prose, same language as the user's note) so it is read "
    "aloud. Remember the note for later if relevant."
)



def wake_pattern(wake):
    word = re.escape(wake)
    return re.compile(
        r"^\s*(?:%s)[\s,]+(?:%s)\b\s*[,:-]?\s*(.*)$"
        % (CONNECTORS, word),
        re.IGNORECASE | re.UNICODE,
    )


def main():
    data = fc.read_stdin_json()
    prompt = str(data.get("prompt", "") or "")
    if not fc.is_enabled():
        return
    # Barge-in: user took the floor, cut the audio now.
    fc.post_to_daemon("/silence", {})
    # Wake word: transform the prompt into a mid-task aside.
    if prompt:
        m = wake_pattern(fc.read_wakeword()).match(prompt)
        if m and m.group(1).strip():
            payload = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": BTW_CONTEXT.format(
                        wake=fc.read_wakeword(), prompt=m.group(1).strip()
                    ),
                }
            }
            print(json.dumps(payload))


if __name__ == "__main__":
    main()
    sys.exit(0)
