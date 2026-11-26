#!/usr/bin/env python3
"""franco_ctl: command-line control for the Franco plugin.

Usage (run through the launcher: bash hooks/run.sh franco_ctl.py <command>):
  enable                          turn speech on (and start the daemon)
  disable                         turn speech off and silence (the daemon stays
                                  running; it is idle and harmless)
  status                          show current state
  set-wakeword <name>             change the wake name (default: franco)
  voices [lang]                   list the curated voices, female and male
  voices --all [locale]           list every voice of the speech service, e.g. it, en-GB
  set-voice <lang> <voice-id>     use a voice for a language ("default" for the rest)
  preview [--voice id] [--lang xx] <text>
                                  speak a test line, e.g. to try a voice first
  silence                         stop the current audio now
  stop                            stop the background daemon (it restarts with
                                  the next session if speech is on)

Settings persist as plain files in ~/.franco/ — nothing to edit by hand.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402

# A small curated set, one female and one male voice at least per language.
# The full catalogue (300+ voices) is available with `voices --all`.
CURATED_VOICES = [
    ("it", "it-IT-ElsaNeural", "female", "warm, clear (default Italian)"),
    ("it", "it-IT-IsabellaNeural", "female", "bright"),
    ("it", "it-IT-DiegoNeural", "male", "calm"),
    ("it", "it-IT-GiuseppeMultilingualNeural", "male", "multilingual"),
    ("en", "en-US-AvaMultilingualNeural", "female", "multilingual (default for other languages)"),
    ("en", "en-US-AndrewMultilingualNeural", "male", "multilingual"),
    ("en", "en-GB-SoniaNeural", "female", "British"),
    ("en", "en-GB-RyanNeural", "male", "British"),
    ("es", "es-ES-ElviraNeural", "female", ""),
    ("es", "es-ES-AlvaroNeural", "male", ""),
    ("fr", "fr-FR-DeniseNeural", "female", ""),
    ("fr", "fr-FR-HenriNeural", "male", ""),
    ("de", "de-DE-TanjaNeural", "female", ""),
    ("de", "de-DE-ChristophNeural", "male", ""),
    ("pt", "pt-BR-FranciscaNeural", "female", "Brazilian"),
    ("pt", "pt-BR-AntonioNeural", "male", "Brazilian"),
]

VOICE_ID_RE = re.compile(r"[A-Za-z]{2,3}-[A-Za-z0-9]{2,8}-[A-Za-z0-9]{1,48}")
LANG_KEY_RE = re.compile(r"default|[a-z]{2,3}(-[a-z0-9]{2,8})?")


def fetch_catalogue(timeout=10):
    """Every voice offered by the speech service, or None if it cannot be reached."""
    if not fc.edge_tts_available():
        return None
    import asyncio

    import edge_tts

    try:
        return asyncio.run(asyncio.wait_for(edge_tts.list_voices(), timeout))
    except Exception:  # noqa: BLE001 — offline, timeout, service change
        return None


def write_wakeword(name):
    with open(fc.config_path("wakeword"), "w", encoding="utf-8") as f:
        f.write(name.strip() + "\n")


def write_voice_map_entry(lang, voice):
    vm = fc.load_voice_map()
    vm[lang] = voice
    vm.setdefault("default", fc.DEFAULT_VOICE_MAP["default"])
    with open(fc.config_path("voice_map.json"), "w", encoding="utf-8") as f:
        json.dump(vm, f, indent=2)


def parse_preview(args):
    """[--voice id] [--lang xx] words... -> (voice or None, lang, text)."""
    voice, lang, words = None, "", []
    it = iter(args)
    for arg in it:
        if arg == "--voice":
            voice = next(it, None)
        elif arg == "--lang":
            lang = next(it, "") or ""
        else:
            words.append(arg)
    return voice, lang, " ".join(words)


def edge_tts_line():
    if not fc.edge_tts_available():
        return "missing (install with: %s)" % fc.install_hint()
    return "installed %s" % (fc.edge_tts_version() or "")


def cmd_status():
    health = fc.daemon_health()
    state = fc.read_daemon_state()
    if health and state:
        daemon = "running on port %s" % state["port"]
        problems = [name for name, key in (("synthesis", "synth"), ("playback", "playback"))
                    if health.get(key) is False]
        if problems:
            daemon += " (last %s failed, see %s)" % (" and ".join(problems), fc.config_path("daemon.log"))
    else:
        daemon = "not running"
    lines = [
        "speech: %s" % ("on" if fc.is_enabled() else "off"),
        "wakeword: %s" % fc.read_wakeword(),
        "voice map: %s" % json.dumps(fc.load_voice_map()),
        "daemon: %s" % daemon,
        "python: %s" % sys.executable,
        "edge-tts: %s" % edge_tts_line(),
    ]
    print("\n".join(lines))


def cmd_voices(rest):
    if rest and rest[0] == "--all":
        prefix = rest[1].lower() if len(rest) > 1 else ""
        catalogue = fetch_catalogue()
        if catalogue is None:
            print("could not reach the speech service (offline, or edge-tts missing: %s)"
                  % fc.install_hint())
            return 1
        rows = sorted(
            (v.get("Locale", ""), v.get("ShortName", ""), v.get("Gender", ""))
            for v in catalogue
            if v.get("Locale", "").lower().startswith(prefix)
        )
        for locale, name, gender in rows:
            print("%-8s %-40s %s" % (locale, name, gender))
        print("%d voices" % len(rows))
        return 0
    filt = rest[0].lower() if rest else ""
    for lang, vid, gender, note in CURATED_VOICES:
        if not filt or filt == lang:
            print("%-3s %-34s %-7s %s" % (lang, vid, gender, note))
    return 0


def cmd_set_voice(rest):
    if len(rest) != 2:
        print("usage: set-voice <lang> <voice-id>   e.g. set-voice it it-IT-DiegoNeural")
        return 2
    lang, voice = rest[0].strip().lower(), rest[1].strip()
    if not LANG_KEY_RE.fullmatch(lang) or not VOICE_ID_RE.fullmatch(voice):
        print("expected a language such as 'it' or 'en-GB' (or 'default') and a voice id "
              "such as it-IT-ElsaNeural")
        return 2
    catalogue = fetch_catalogue()
    warning = ""
    if catalogue is None:
        warning = " (could not check the voice against the speech service; offline?)"
    elif voice not in {v.get("ShortName") for v in catalogue}:
        print("unknown voice: %s. Browse the available ones with: voices --all %s"
              % (voice, lang if lang != "default" else ""))
        return 1
    write_voice_map_entry(lang, voice)
    print("voice for '%s' is now %s%s" % (lang, voice, warning))
    return 0


def cmd_preview(rest):
    voice, lang, text = parse_preview(rest)
    if not text:
        print('usage: preview [--voice id] [--lang xx] <text>   e.g. preview --voice it-IT-DiegoNeural "Ciao"')
        return 2
    if voice is not None and not VOICE_ID_RE.fullmatch(voice):
        print("not a voice id: %s" % voice)
        return 2
    if not fc.is_enabled():
        print("speech is off — run 'enable' first")
        return 1
    if not fc.ensure_daemon():
        print("daemon did not start; see %s" % fc.config_path("daemon.log"))
        return 1
    payload = {"text": text, "lang": lang}
    if voice:
        payload["voice"] = voice
    if not fc.post_to_daemon("/say", payload, timeout=10.0):
        print("could not reach the daemon")
        return 1
    print("queued for playback with %s" % (voice or fc.voice_for_lang(lang)))
    return 0


def main(argv):
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    os.makedirs(fc.CONFIG_DIR, exist_ok=True)

    if cmd == "enable":
        open(fc.config_path("enabled"), "w").close()
        if not fc.edge_tts_available():
            print("speech on, but edge-tts is missing for this Python. Install it with:\n  %s"
                  % fc.install_hint())
            return 1
        if not fc.ensure_daemon():
            print("speech on, but the daemon did not start; see %s" % fc.config_path("daemon.log"))
            return 1
        print("speech on (daemon running; new sessions speak automatically)")
        return 0
    if cmd == "disable":
        try:
            os.unlink(fc.config_path("enabled"))
        except OSError:
            pass
        fc.post_to_daemon("/silence", {}, timeout=1.0)
        print("speech off")
        return 0
    if cmd == "status":
        cmd_status()
        return 0
    if cmd == "set-wakeword":
        if not rest or not " ".join(rest).strip():
            print("usage: set-wakeword <name>")
            return 2
        write_wakeword(" ".join(rest))
        print("wake word is now: %s" % fc.read_wakeword())
        return 0
    if cmd == "set-voice":
        return cmd_set_voice(rest)
    if cmd == "voices":
        return cmd_voices(rest)
    if cmd == "silence":
        fc.post_to_daemon("/silence", {}, timeout=1.0)
        print("silenced")
        return 0
    if cmd == "stop":
        if fc.daemon_health() is None:
            print("daemon is not running")
            return 0
        if not fc.post_to_daemon("/shutdown", {}, timeout=2.0):
            print("could not reach the daemon")
            return 1
        print("daemon stopped")
        return 0
    if cmd == "preview":
        return cmd_preview(rest)
    print("unknown command: %s\n%s" % (cmd, __doc__))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
