<div align="center">

# Franco

### A voice for Claude Code

Franco reads a short summary of each Claude Code reply aloud with natural
neural voices, stops the audio as soon as you send your next prompt, and lets
you address Claude by name to add a note without interrupting its work.

[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-0.1.0--alpha.1-orange.svg)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-0078D6.svg)](#requirements)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](#requirements)
[![Claude Code plugin](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](https://claude.com/claude-code)

**English** · [Italiano](README.it.md)

</div>

<!-- Demo: add a short screen recording with audio here before the announcement. -->

---

## Why Franco

Claude Code already accepts voice input, through its built-in dictation or
tools such as Wispr Flow, but its answers are text only. If you work by voice,
step away from the screen, or simply want to hear "done" while you look at
something else, you still have to read every reply.

Franco closes that loop. At the end of each conversational reply Claude writes
a one- or two-sentence summary meant for a listener, and Franco speaks it.
Code, tables and diffs are not read aloud.

## Features

| | |
|---|---|
| **Spoken summaries** | Claude ends conversational replies with a short plain-prose summary in a `<spoken>` tag, which Franco reads aloud. Replies that are mostly code, tables or file dumps get no summary and stay silent. |
| **Italian first, multilingual** | Curated female and male voices for Italian, English, Spanish, French, German and Portuguese, and 300+ more in the full catalogue. Claude declares the language of each summary (`<spoken lang="it">`), so no language detection is involved. |
| **Barge-in** | Sending a new prompt stops the current audio immediately. No hotkey to remember. |
| **Wake name** | Start a message with `Comunque Franco, …` (or `By the way Franco, …`) to add a note: Claude acknowledges it in one spoken line and keeps working. The name is configurable. `/franco:btw <note>` does the same. |
| **Warm local service** | A small background process on `127.0.0.1`, protected by a per-run token, synthesises and plays the audio so replies are not delayed by Python start-up. |
| **Free, no account** | Voices come from Microsoft's online neural text-to-speech through the open-source [`edge-tts`](https://github.com/rany2/edge-tts) library. No API key or subscription. |

## Requirements

- **Windows 10 or 11.** Audio playback uses the Windows Media Control
  Interface. macOS and Linux are on the roadmap.
- **Claude Code** with plugin support. Tested with 2.1.332.
- **Python 3.10 or later**, installed from [python.org](https://www.python.org/downloads/windows/)
  (recommended, it includes the `py` launcher) or any other distribution.
  Tested end to end with 3.14; the test suite also runs on 3.10.
- **An internet connection** while speech is on: synthesis is an online service.

## Install

**1. Add the marketplace and install the plugin**

```bash
claude plugin marketplace add davideferrari/claude_franco
claude plugin install franco@claude-franco
```

The same is available inside Claude Code with `/plugin`. To try a local
checkout without installing it, start Claude Code with
`claude --plugin-dir <path-to-checkout>`.

**2. Install the speech library into the Python that Franco will use**

```powershell
py -3 -m pip install "edge-tts>=7.0,<8"
```

Franco looks for Python in this order: the `FRANCO_PYTHON` environment
variable, `py -3`, `python3`, `python`. The Microsoft Store "App execution
alias" placeholders are detected and skipped. If you use a virtual
environment or a specific interpreter, point `FRANCO_PYTHON` at its
`python.exe`.

**3. Turn speech on**

In Claude Code:

```text
/franco:franco on
```

Franco checks the dependency, starts its background service and confirms. If
something is missing, it tells you the exact command to run. Speech applies to
the current session straight away and to every new session.

## Usage

| Command | What it does |
|---|---|
| `/franco:franco` | Show the current state: speech, wake name, voices, service, Python, `edge-tts` |
| `/franco:franco on` · `off` | Turn speech on or off |
| `/franco:franco silence` | Stop the current audio; speech stays on |
| `/franco:franco stop` | Shut the background service down; it restarts with the next session while speech is on |
| `/franco:franco voice` | Choose a voice per language, with a sample to listen to first |
| `/franco:franco wakeword` | Change the name Claude answers to (default: Franco) |
| `/franco:btw <note>` | Add a note while Claude is working |

You can also just ask in plain language ("mute", "use a male Italian voice",
"call yourself Alfredo"): the bundled `franco` skill maps the request to the
right setting.

> Claude Code also has its own built-in `/btw` for quick side questions.
> Franco's variant is namespaced as `/franco:btw` and is acknowledged aloud.

The same controls are available from a terminal, run from the plugin folder:

```bash
bash hooks/run.sh franco_ctl.py status
bash hooks/run.sh franco_ctl.py set-voice it it-IT-DiegoNeural
bash hooks/run.sh franco_ctl.py preview --lang it "Ciao, sono Franco."
```

## Voices

Each language has its own voice; Claude picks the language of every summary,
and Franco uses the voice you chose for it. The curated set:

| Language | Female | Male |
|---|---|---|
| Italian | `it-IT-ElsaNeural` (default), `it-IT-IsabellaNeural` | `it-IT-DiegoNeural`, `it-IT-GiuseppeMultilingualNeural` |
| English | `en-US-AvaMultilingualNeural` (default), `en-GB-SoniaNeural` | `en-US-AndrewMultilingualNeural`, `en-GB-RyanNeural` |
| Spanish | `es-ES-ElviraNeural` | `es-ES-AlvaroNeural` |
| French | `fr-FR-DeniseNeural` | `fr-FR-HenriNeural` |
| German | `de-DE-TanjaNeural` | `de-DE-ChristophNeural` |
| Portuguese (Brazil) | `pt-BR-FranciscaNeural` | `pt-BR-AntonioNeural` |

`/franco:franco voice` walks you through it and plays a sample before you
commit. Or just ask: "use a male Italian voice". For other accents and
languages, browse the full catalogue of the speech service:

```bash
bash hooks/run.sh franco_ctl.py voices --all en-GB
bash hooks/run.sh franco_ctl.py preview --voice en-GB-ThomasNeural "Hello, I am Franco."
bash hooks/run.sh franco_ctl.py set-voice en en-GB-ThomasNeural
```

`set-voice` checks the id against the catalogue, so a typo or a retired voice
is reported instead of failing silently. Languages without a voice of their
own use the `default` entry (`set-voice default <voice-id>`).

## How it works

```text
You send a prompt ──▶ UserPromptSubmit hook ──▶ stop current audio (barge-in)
                                         └──▶ wake name? ──▶ add "note" context
Claude replies ──▶ <spoken lang="…"> tag ──▶ Stop hook ──▶ local service
                                                              ├─ edge-tts synthesis
                                                              └─ Windows playback
Session starts ──▶ SessionStart hook ──▶ add the <spoken> rule + start the service
```

1. When speech is on, the **SessionStart** hook adds a short instruction to
   Claude's context: end conversational replies with a `<spoken>` summary in
   plain prose, and skip it for data-shaped replies.
2. The **Stop** hook takes the final reply of the turn, extracts the last
   `<spoken>` tag and hands it to the local service.
3. The service synthesises the text with the voice mapped to the declared
   language and plays it. Playback is serialised and the queue is short, so
   speech never lags far behind.
4. The **UserPromptSubmit** hook stops the audio whenever you send a prompt and
   recognises the wake name pattern.

While speech is off, the hooks return immediately without starting Python.
Only one service runs per user; after a plugin update, a service still running
the previous version is replaced automatically.

## Configuration

Settings are plain files in `%USERPROFILE%\.franco\`, managed through the
commands above:

| File | Purpose |
|---|---|
| `enabled` | Present while speech is on |
| `wakeword` | The wake name |
| `voice_map.json` | Language → voice, e.g. `{"it": "it-IT-ElsaNeural", "default": "en-US-AvaMultilingualNeural"}` |
| `python` | The interpreter Franco found; delete it to search again |
| `daemon.state`, `daemon.lock`, `daemon.log` | Service port and token, single-instance lock, log |
| `last_spoken` | Hash of the last summary, so a turn is never spoken twice |

| Environment variable | Purpose |
|---|---|
| `FRANCO_PYTHON` | Full path of the Python interpreter to use |
| `FRANCO_HOME` | Alternative settings folder, useful for testing |

## Privacy and data

Please read this before turning speech on.

- **What leaves your machine:** only the text inside each `<spoken>` tag. It
  is sent to Microsoft's speech service (`speech.platform.bing.com`) to be
  synthesised. Your prompts, files and the rest of each reply are not sent
  by Franco.
- **The summary is written by the model.** Claude is instructed to keep it to
  plain prose without code, commands or long numbers, but Franco cannot
  guarantee what a summary contains. Its text clean-up removes formatting
  only. It is **not** a filter for secrets or personal data. As a safeguard,
  a summary that contains code, a table or markup, or is unusually long, is
  not spoken at all, and tags shown inside code blocks are ignored. If you work with
  confidential material, keep speech off for that session.
- **Unofficial service.** `edge-tts` uses the endpoint behind the Read Aloud
  feature of Microsoft Edge. It is free and needs no account, but it is not a
  supported public API and may change or stop working without notice.
- **What stays local:** settings and a log in `%USERPROFILE%\.franco\`. The
  log records language, voice, length and outcome of each utterance, never
  its text. Audio files are temporary and deleted after playback.
- **Local service:** listens on `127.0.0.1` only. Every command it accepts
  requires a random token that is regenerated at each start.

Details, and how to report a vulnerability, are in [SECURITY.md](SECURITY.md).

## Known limitations

Franco is an **alpha** release:

- **Windows only** for now.
- **Settings are per user, not per project.** Speech on or off, voices and
  the wake name apply to every Claude Code session. With two sessions open,
  sending a prompt in one also stops audio started by the other.
- **The wake name is matched in the text you send**, typed or dictated. Franco
  does not listen to the microphone.
- **Barge-in happens when a prompt is sent**, not when you start speaking.
- **Summaries depend on the model** following the instruction. When it skips
  the tag, the reply is simply not spoken.
- **Non-interactive runs (`claude -p`) are not spoken:** the session ends, and
  its audio is stopped, right after the reply.

## Troubleshooting

| Symptom | What to do |
|---|---|
| "no working Python 3.10+ found" at session start | Install Python from python.org, or set `FRANCO_PYTHON` to your interpreter's `python.exe`. |
| "edge-tts is not installed for …" | Run the command shown in the message: it installs into the interpreter Franco is using. |
| Nothing is spoken | Run `/franco:franco` and check that speech is on and the service is running, then look at `%USERPROFILE%\.franco\daemon.log`. Speech starts with replies that contain a summary. |
| Wrong Python after installing a new one | Delete `%USERPROFILE%\.franco\python`, or set `FRANCO_PYTHON`. |

## Uninstall

In Claude Code, run `/franco:franco off` and then `/franco:franco stop`.
Then, from a terminal:

```bash
claude plugin uninstall franco@claude-franco
claude plugin marketplace remove claude-franco
```

Then delete `%USERPROFILE%\.franco\` to remove settings and logs, and
optionally `py -3 -m pip uninstall edge-tts`.

## Roadmap

- macOS and Linux playback (synthesis is already cross-platform)
- Sentence-by-sentence streaming synthesis
- Offline voices (Windows SAPI, Piper) as an alternative to the online service
- Per-project settings
- `/speak-full` to read a whole reply aloud

## Contributing

Issues and pull requests are welcome, including new voices for the language
map. Please report security issues privately as described in
[SECURITY.md](SECURITY.md). Run the checks before opening a pull request:

```bash
py -3 tests/run_all.py
claude plugin validate .
```

## Acknowledgements

Speech synthesis by [`edge-tts`](https://github.com/rany2/edge-tts). Franco is
an independent project, not affiliated with or endorsed by Anthropic or
Microsoft.

## License

[MIT](LICENSE) © 2026 Davide Ferrari
