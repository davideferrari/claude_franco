# Security and privacy

## Reporting a vulnerability

Please do not open a public issue for security problems. Use GitHub's
[private vulnerability reporting](https://github.com/davideferrari/claude_franco/security/advisories/new)
instead. Include the Franco version, your Windows and Python versions, and the
steps to reproduce. You can expect an acknowledgement within a week.

Only the latest release is supported with fixes during the alpha phase.

## What Franco sends and stores

| Data | Where it goes |
|---|---|
| Text inside each `<spoken>` tag | Sent to Microsoft's speech service (`speech.platform.bing.com`) through `edge-tts` for synthesis |
| Your prompts, files, the rest of each reply | Not sent anywhere by Franco |
| Settings and service files (`enabled`, `wakeword`, `voice_map.json`, `python`, `daemon.state`, `daemon.lock`, `last_spoken`, a hash of the last summary) | `%USERPROFILE%\.franco\` |
| Service log | `%USERPROFILE%\.franco\daemon.log`: start/stop events, errors and, per utterance, language, voice, length and outcome. Never the spoken text |
| Synthesised audio | A temporary file, deleted after playback |

The summary is written by the model following Franco's instruction (plain
prose, no code, commands or long numbers). Franco removes formatting before
synthesis, and refuses to speak a summary that contains code, a table or
markup, or is unusually long; tags shown inside code blocks are ignored. It
does not detect secrets or personal data. If you work with
confidential material, turn speech off with `/franco:franco off`.

`edge-tts` relies on the endpoint behind Microsoft Edge's Read Aloud feature.
It is not an officially supported API: its availability and terms may change
without notice. An offline alternative (Windows SAPI or Piper) is planned but
not yet available.

## Local service

The background service binds to `127.0.0.1` on a random port. Every command
that changes state (`/say`, `/silence`, `/shutdown`) requires a 128-bit token
generated at each start and stored in `%USERPROFILE%\.franco\daemon.state`,
which is readable by your Windows user account. `/health` is unauthenticated
and reveals only whether the service is up and how many items are queued.
