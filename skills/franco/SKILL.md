---
name: franco
description: Voice control for the Franco plugin — turn spoken replies on or off, change voice or wake name, stop the audio, or take a mid-task note. Use when the user says things like "make Claude talk", "turn on TTS", "mute", "stop speaking", "switch voice", "be quiet", or addresses Claude by its wake name (e.g. "Comunque Franco, ...") to add a note while work continues.
---

Franco gives Claude Code spoken replies. Run its control CLI with the **Bash
tool**, always through the launcher (it selects the right Python):

```
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" franco_ctl.py <command> [args]
```

Map what the user wants to a command:

| User says | Command |
|---|---|
| "make Claude talk", "turn on speech/TTS" | `enable` |
| "mute", "turn speech off" | `disable` |
| "stop talking right now", "be quiet", "silence" | `silence` (speech stays on) |
| "switch to <voice>", "use a male/British/Italian voice" | `voices [lang]` to list, then `set-voice <lang> <id>` |
| "what voices are there" | `voices` |
| "call yourself <name>", "change the wake name to <name>" | `set-wakeword <name>` |
| "how is speech configured", "franco status" | `status` |
| Addresses you by the wake name mid-task ("Comunque Franco, nota questo") | No command: treat it as a note — acknowledge in one line with a `<spoken>` tag and keep working |

Rules:

- If a command exits with an error, report its message (including any install
  command it prints) instead of claiming success.
- After a successful `enable`, speech is live for the rest of this session:
  end each conversational reply with a `<spoken lang="xx">` tag of 1–2 plain
  sentences in the reply's language. After `disable`, stop adding the tag.
- Confirm every change in one short line; if speech is on, add a `<spoken>`
  tag with that line so it is heard.
- Never put code, tables, paths or commands inside the `<spoken>` tag.
