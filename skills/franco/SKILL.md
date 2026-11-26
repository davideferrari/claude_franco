---
name: franco
description: Voice control for the Franco plugin — turn spoken replies on/off, change voice or wake word, interrupt audio, or note down a mid-task aside. Use when the user says things like "make Claude talk", "turn on TTS", "mute", "stop speaking", "switch voice", "stop talking right now", or calls Claude by its wake name (e.g. "Comunque Franco, ...") to note something mid-task.
---

Franco gives Claude Code spoken replies. Control CLI:
`$CLAUDE_PLUGIN_ROOT/hooks/franco_ctl.py` (run with `python`). Config in `~/.franco/`.

Map what the user wants to a command:

| User says | Do |
|---|---|
| "make Claude talk", "turn on speech/TTS" | `enable` |
| "mute", "stop speaking", "silence" | `disable` (or `silence` if they mean just now) |
| "stop talking right now", "be quiet" | `silence` |
| "switch to <voice>", "use a male/British/Italian voice" | `voices [lang]` to list, then `set-voice <lang> <id>` |
| "what voices are there", "list voices" | `voices` |
| "call yourself <name>", "change the wake word to <name>" | `set-wakeword <name>` |
| "how is speech configured", "franco status" | `status` |
| Calls you by the wake name mid-task (e.g. "Comunque Franco, nota questo") | Behave like `/btw <phrase>`: acknowledge in one line + `<spoken>` tag, keep working |

Rules:

- Confirm every change in one short line. If speech is enabled, append a
  `<spoken lang="xx">` tag with that line so the confirmation is heard.
- After `enable`, remind the user (once) that speech applies from the next
  session start, or immediately if the daemon just got started.
- Never put code, tables, or commands inside the `<spoken>` tag.
