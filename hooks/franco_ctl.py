#!/usr/bin/env python3
"""franco_ctl: command-line control for the Franco plugin.

Usage:
  python franco_ctl.py enable                 turn speech on (and start the daemon)
  python franco_ctl.py disable                turn speech off and silence (the daemon
                                              stays running; it is idle and harmless)
  python franco_ctl.py status                 show current state
  python franco_ctl.py set-wakeword <name>    change the wake word (default: franco)
  python franco_ctl.py set-voice <lang> <id>  map a language to an edge-tts voice
  python franco_ctl.py voices [lang]          list curated voices (filter by lang)
  python franco_ctl.py silence                stop the current audio now
  python franco_ctl.py preview <text>         synthesise and play a test line

Settings persist as plain files in ~/.franco/ — nothing to edit by hand.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import franco_common as fc  # noqa: E402

# A small curated set; the full edge-tts catalogue is far larger.
CURATED_VOICES = [
    ("it", "it-IT-ElsaNeural", "female, warm (default Italian)"),
    ("it", "it-IT-GiuseppeNeural", "male, calm"),
    ("it", "it-IT-IsabellaNeural", "female, bright"),
    ("en", "en-US-AvaMultilingualNeural", "female, multilingual (default fallback)"),
    ("en", "en-US-AndrewMultilingualNeural", "male, multilingual"),
    ("en", "en-GB-RyanNeural", "male, British"),
    ("en", "en-GB-SoniaNeural", "female, British"),
    ("es", "es-ES-ElviraNeural", "female"),
    ("fr", "fr-FR-DeniseNeural", "female"),
    ("de", "de-DE-KatjaNeural", "female"),
    ("pt", "pt-BR-FranciscaNeural", "female"),
]


def write_wakeword(name):
    with open(fc.config_path("wakeword"), "w", encoding="utf-8") as f:
        f.write(name.strip() + "\n")


def write_voice_map_entry(lang, voice):
    vm = fc.load_voice_map()
    vm[lang.lower()] = voice.strip()
    vm.setdefault("default", fc.DEFAULT_VOICE_MAP["default"])
    with open(fc.config_path("voice_map.json"), "w", encoding="utf-8") as f:
        json.dump(vm, f, indent=2)


def edge_tts_line():
    if not fc.edge_tts_available():
        return "missing (install with: %s)" % fc.install_hint()
    return "installed %s" % (fc.edge_tts_version() or "")


def cmd_status():
    health = fc.daemon_health()
    state = fc.read_daemon_state()
    if health and state:
        daemon = "running on port %s" % state["port"]
        if health.get("synth") is False:
            daemon += " (last synthesis failed, see %s)" % fc.config_path("daemon.log")
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
        if not rest:
            print("usage: set-wakeword <name>")
            return 2
        write_wakeword(" ".join(rest))
        print("wake word is now: %s" % fc.read_wakeword())
        return 0
    if cmd == "set-voice":
        if len(rest) != 2:
            print("usage: set-voice <lang> <voice-id>")
            return 2
        write_voice_map_entry(rest[0], rest[1])
        print("voice map updated: %s" % json.dumps(fc.load_voice_map()))
        return 0
    if cmd == "voices":
        filt = (rest[0].lower() if rest else "")
        for lang, vid, note in CURATED_VOICES:
            if not filt or filt == lang:
                print("%-3s %-34s %s" % (lang, vid, note))
        return 0
    if cmd == "silence":
        fc.post_to_daemon("/silence", {}, timeout=1.0)
        print("silenced")
        return 0
    if cmd == "preview":
        if not rest:
            print("usage: preview <text>")
            return 2
        if not fc.is_enabled():
            print("speech is off — run 'franco_ctl.py enable' first")
            return 1
        if not fc.ensure_daemon():
            print("daemon did not start; see %s" % fc.config_path("daemon.log"))
            return 1
        if not fc.post_to_daemon("/say", {"text": " ".join(rest), "lang": ""}, timeout=10.0):
            print("could not reach the daemon")
            return 1
        print("queued for playback")
        return 0
    print("unknown command: %s\n%s" % (cmd, __doc__))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
