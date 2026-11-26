---
description: Franco voice controls — turn speech on or off, pick a voice, change the wake name
argument-hint: "[on | off | status | voice | wakeword | silence | stop]"
---

You are the control menu for the Franco speech plugin.

Run the control CLI with the **Bash tool** (not PowerShell), always through the
launcher, which picks the right Python interpreter:

```
bash "${CLAUDE_PLUGIN_ROOT}/hooks/run.sh" franco_ctl.py <command> [args]
```

The user's argument is: $ARGUMENTS

Behaviour:

- No argument or `status`: run `status` and present it as a short table
  (speech, wake name, voice map, daemon, Python, edge-tts), then list the
  options below in one line.
- `on`: run `enable`.
  - If it exits with an error, show the message and the exact install command
    it printed; do not claim speech is on and working.
  - If it succeeds, speech is live for the rest of this session too: from now
    on, end every conversational reply with a `<spoken lang="xx">` tag holding
    1–2 sentences of plain prose that summarise the reply for a listener — no
    markdown, code, commands or long numbers; same language as the reply.
    Replies that are mostly code, tables, diffs or file dumps get no tag.
- `off`: run `disable`. Stop adding `<spoken>` tags for the rest of this session.
- `silence`: run `silence` to stop the current audio.
- `stop`: run `stop` to shut the background service down (for example before
  uninstalling). If speech is still on, it restarts with the next session.
- `voice`: run `voices`, show the list numbered, ask which one to use, then run
  `set-voice <lang> <voice-id>` (the lang is the voice id's prefix, e.g. `it`).
- `wakeword`: ask which name they want to use, run `set-wakeword <name>`, and
  confirm with an example: "Comunque <name>, …" adds a note while I keep working.

Confirm every outcome in one line. If speech is on, end the reply with a
`<spoken lang="xx">` tag reading that confirmation aloud.
