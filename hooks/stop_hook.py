#!/usr/bin/env python3
"""Stop hook: reads the transcript, extracts the last <spoken> tag, sends it to the daemon.

Never blocks or fails loudly: any problem means "no speech this turn", nothing more.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402


def read_stdin_json():
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except (ValueError, OSError):
        return {}


def last_assistant_text(transcript_path, attempts=2):
    """Pull the text of the last assistant message from the transcript JSONL."""
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
                    if entry.get("type") != "assistant":
                        continue
                    msg = entry.get("message") or {}
                    parts = []
                    for block in msg.get("content") or []:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
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


def main():
    data = read_stdin_json()
    if not fc.is_enabled():
        return  # speech off: nothing to do, silently
    transcript_path = data.get("transcript_path") or ""
    if not transcript_path or not os.path.exists(transcript_path):
        return
    text = last_assistant_text(transcript_path)
    if not text:
        return
    lang, summary = fc.extract_spoken(text)
    if not summary:
        return  # data-shaped reply (no tag): silent by design
    if len(summary) > fc.MAX_TEXT_LEN:
        summary = summary[: fc.MAX_TEXT_LEN]
    fc.post_to_daemon("/say", {"text": summary, "lang": lang or ""})


if __name__ == "__main__":
    main()
    sys.exit(0)
