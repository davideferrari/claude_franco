# Changelog

All notable changes to Franco are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0-alpha.1] — unreleased

First public preview. Windows only.

### Added

- Spoken summaries: Claude ends conversational replies with a `<spoken>` tag
  that is read aloud with Microsoft neural voices through `edge-tts`.
- Language-to-voice map with curated female and male voices for Italian,
  English, Spanish, French, German and Portuguese; `voices --all` browses the
  full catalogue, `preview --voice` plays a sample, and `set-voice` rejects
  unknown or retired voice ids.
- Barge-in: sending a prompt stops the current audio.
- Wake name ("Comunque Franco, …") and `/franco:btw` for mid-task notes.
- `/franco:franco` control menu and the `franco` skill for natural-language
  control; `franco_ctl.py` command-line tool, including `status`, `preview`
  and `stop`.
- Background service on `127.0.0.1` with a per-run token and a short,
  serialised playback queue.
- `hooks/run.sh` launcher that finds a working Python 3.10+ and skips the
  Microsoft Store placeholders; `FRANCO_PYTHON` override.
- Clear messages when Python or `edge-tts` is missing or the service does
  not start.
- Conservative speech policy: tags inside code are ignored, and summaries
  containing code, tables or markup are not spoken; each turn is spoken once.
- Single service per user (lock file), atomic state file, validated HTTP
  input, network timeouts, and automatic replacement of a service left
  running by a previous version.

### Known limitations

- Windows only; settings are shared by all sessions of the same user.
- Requires an internet connection; the speech endpoint is not an officially
  supported Microsoft API.
- Non-interactive runs (`claude -p`) end before the audio is played.

[0.1.0-alpha.1]: https://github.com/davideferrari/claude_franco/releases
