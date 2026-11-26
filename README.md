<div align="center">

# 🎙️ Franco

**Give Claude Code a name and a voice.**

Franco speaks back. Neural voices summarise each response aloud, playback
cuts the instant you take the floor, and you can call Claude by its name to
drop a mid-task note without breaking its flow.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)]()
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078D6.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)]()
[![Claude Code](https://img.shields.io/badge/for-Claude%20Code-d97757.svg)]()

*Italian-first, multilingual · Free neural voices · Zero accounts*

**🇬🇧 English** · [🇮🇹 Italiano](README.it.md)

</div>

---

> Claude Code already has voice **dictation** on the input side (`/voice`),
> but nothing speaks back. Pair your dictation (Claude Code's own, or
> WhisperFlow) with Franco and you get a genuine **two-way conversation in
> the terminal**.
>
> <!-- TODO: add a demo GIF here before publishing -->

## ✨ Highlights

|  | Feature | What it means |
|---|---------|---------------|
| 🔊 | **Spoken summaries** | Claude ends conversational replies with a short prose summary, spoken by a neural voice. Code, tables and file dumps **never** get read — they don't get a tag, by design. |
| 🇮🇹 | **Italian-first, multilingual** | Curated Italian voices (`it-IT-ElsaNeural`, `it-IT-GiuseppeNeural`), more languages behind a `lang → voice` map. Claude itself declares the language (`<spoken lang="it">`) — no detection library, no misfires. |
| ⚡ | **Barge-in** | Submitting a new prompt stops the current audio instantly. Taking the floor *is* the interruption — no hotkey to remember. |
| 🙋 | **Wake name** | While Claude works, say or type `Comunque Franco, <note>`. It acknowledges aloud in one line and keeps working. Also available as `/btw <note>`. |
| 🔥 | **Warm daemon** | A token-authenticated localhost daemon synthesises and plays — no Python/TLS cold start on every reply. |
| 🔓 | **Free & account-less** | Microsoft Edge neural voices via `edge-tts`. No subscription, no API key, no account. |

## 📦 Install

Franco is a [Claude Code](https://claude.com/claude-code) plugin.

**From a local checkout:**

```jsonc
// ~/.claude/settings.json
{
  "extraKnownMarketplaces": {
    "franco": {
      "source": { "source": "directory", "path": "/absolute/path/to/claude-franco" }
    }
  },
  "enabledPlugins": {
    "franco@franco": true
  }
}
```

```bash
claude plugin install franco@franco
```

**Requirements**

- Windows 10/11 (playback uses MCI; macOS/Linux is planned for v2)
- Python 3.10+ on PATH
- `pip install edge-tts` — free neural TTS; synthesis is a network call, so it needs internet

## 🚀 Quick start

```text
/franco on          # turn speech on (also starts the daemon)
/franco voice       # browse and pick a voice
/franco wakeword    # choose the name Claude answers to
/franco off         # mute
```

Or with the CLI:

```bash
python hooks/franco_ctl.py enable
python hooks/franco_ctl.py status
python hooks/franco_ctl.py set-wakeword "Alfredo"
python hooks/franco_ctl.py silence
```

## ⚙️ How it works

```
user speaks/types ──▶ UserPromptSubmit hook ──▶ barge-in (daemon silences)
                                         └─▶ wake word? ──▶ "btw" aside
Claude replies ──▶ <spoken> tag ──▶ Stop hook ──▶ warm localhost daemon
                                                        └─▶ edge-tts + MCI playback
SessionStart hook ──▶ injects <spoken> rule (if enabled) + ensures daemon is up
```

1. A **SessionStart hook** injects the `<spoken>` emission rule (only where
   speech is enabled) and ensures the daemon is running.
2. Claude ends conversational replies with `<spoken lang="xx">…</spoken>`
   (plain prose, 1–2 sentences, no markdown).
3. The **Stop hook** extracts the tag from the transcript and POSTs it to the
   daemon, which synthesises it with the voice mapped to the language and
   plays it (MCI on Windows).
4. The **UserPromptSubmit hook** implements the conversation feel: barge-in on
   every new prompt, and wake-name detection turns `Comunque Franco, …` into a
   mid-task aside (same behaviour as `/btw`).

Speech is **off by default** and opt-in. Data-shaped replies (code, tables,
dumps) are silent by design — if the model "forgets" the tag, the response is
simply not spoken: silent degradation, never noisy.

## 🔒 Privacy & security

- Your **code, tables and file dumps are never sent anywhere**: they never get
  a `<spoken>` tag. Only the short prose summary leaves your machine.
- The summary is synthesised by Microsoft's `edge-tts` backend (the
  undocumented service behind Edge's Read Aloud — free, account-less, but not
  a supported API; it may change without notice). Fallbacks are documented in
  [`INTENT.md`](INTENT.md).
- The daemon listens on `127.0.0.1` only and is token-authenticated.

## 🗺️ Roadmap

Shipped in **v0.1.0** — the full end-to-end voice loop.

Planned for **v2**:

- [ ] macOS/Linux playback (synthesis is already cross-platform)
- [ ] Streaming synthesis, sentence by sentence
- [ ] Offline fallback (SAPI / Piper)
- [ ] `/speak-full` — read the entire response aloud

## 🤝 Contributing

Open to anyone — issues, PRs and new voices for the `lang → voice` map are
welcome. Keep it friendly.

## 📄 License

Released under the [MIT License](LICENSE) — **free to use, modify and share,
for everyone**. That means you, your team, your side project and your company.

<div align="center">

*Built for people who talk to their terminal.*

</div>
