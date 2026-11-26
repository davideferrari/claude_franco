#!/usr/bin/env python3
"""Stop hook: takes the final reply of the turn, extracts its <spoken> tag and
sends it to the daemon.

The reply comes from the payload's `last_assistant_message`. Claude Code may
run this hook before the final text reaches the transcript, so the transcript
is only a fallback for versions without that field — and even then only the
current turn is considered, so an older summary is never replayed.

Never blocks or fails loudly: any problem means "no speech this turn", nothing more.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402


def _is_user_prompt(entry):
    """True for a real user turn; tool results are also stored as type 'user'."""
    if entry.get("type") != "user":
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    return isinstance(content, list) and any(
        isinstance(b, dict) and b.get("type") == "text" for b in content
    )


def last_assistant_text(transcript_path, attempts=2):
    """Text of the last assistant message of the current turn, from the transcript JSONL."""
    for attempt in range(attempts):
        try:
            best = None
            with open(transcript_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    if not isinstance(entry, dict):
                        continue
                    if _is_user_prompt(entry):
                        best = None  # a new turn starts: forget earlier replies
                        continue
                    if entry.get("type") != "assistant":
                        continue
                    msg = entry.get("message") or {}
                    parts = [
                        block.get("text", "")
                        for block in msg.get("content") or []
                        if isinstance(block, dict) and block.get("type") == "text"
                    ]
                    if parts:
                        best = "\n".join(parts)
            if best:
                return best
        except OSError:
            pass
        # Transcript is written asynchronously — give it a moment, retry once.
        if attempt + 1 < attempts:
            time.sleep(0.4)
    return ""


def turn_text(data):
    """Final reply text of the turn that just ended."""
    message = data.get("last_assistant_message")
    if isinstance(message, str) and message.strip():
        return message
    transcript_path = data.get("transcript_path") or ""
    if transcript_path and os.path.exists(transcript_path):
        return last_assistant_text(transcript_path)
    return ""


def main():
    data = fc.read_stdin_json()
    if not fc.is_enabled():
        return  # speech off: nothing to do, silently
    text = turn_text(data)
    if not text:
        return
    lang, summary = fc.extract_spoken(text)
    if not summary:
        return  # data-shaped reply (no tag): silent by design
    fc.post_to_daemon("/say", {"text": summary[: fc.MAX_TEXT_LEN], "lang": lang or ""})


if __name__ == "__main__":
    main()
    sys.exit(0)
