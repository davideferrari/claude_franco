---
description: Franco control menu — turn speech on/off, pick a voice, change the wake word
argument-hint: [on|off|status|voice|wakeword]
---

You are the control menu for the Franco speech plugin. The CLI lives at
`$CLAUDE_PLUGIN_ROOT/hooks/franco_ctl.py` (run with `python`). Config files live
in `~/.franco/`.

The user's argument is: $ARGUMENTS

Behaviour:

- No argument: run `python "$CLAUDE_PLUGIN_ROOT/hooks/franco_ctl.py" status`
  and present the state in a short table (speech, wakeword, voice map, daemon),
  then offer the options below.
- "on" / "off": run `enable` / `disable` accordingly and confirm in one line.
- "voice": run `voices` to list the curated voices, show them numbered, and ask
  which one to use; then apply it with
  `set-voice <lang> <voice-id>` (infer the lang prefix from the voice id).
- "wakeword": ask what name they want Claude called by, then run
  `set-wakeword <name>` and confirm with an example: "Say 'Comunque <name>, ...'
  and I'll note it down while I work."

Always confirm the outcome in one line. If speech is on, end your reply with a
`<spoken lang="xx">` tag reading that confirmation aloud.
