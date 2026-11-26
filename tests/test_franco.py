#!/usr/bin/env python3
"""Unit tests for Franco's pure logic: sanitiser, <spoken> extraction, voice
mapping, wake-word pattern, and Stop-hook transcript parsing.

Run: python tests/test_franco.py
No audio, no network, no daemon required.
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hooks"))

import franco_common as fc  # noqa: E402
import prompt_hook as ph  # noqa: E402
import stop_hook as sh  # noqa: E402

FAILURES = []


def check(name, condition, detail=""):
    if condition:
        print("  ok  %s" % name)
    else:
        FAILURES.append(name)
        print("FAIL  %s %s" % (name, detail))


# --- sanitiser ----------------------------------------------------------------
check("sanitise strips code fences", "```py\ncode()\n```" not in fc.sanitise("a ```py\ncode()\n``` b"))
check("sanitise strips bold", "**pippo**" not in fc.sanitise("ciao **pippo** come"))
check("sanitise strips inline code", "`ls -la`" not in fc.sanitise("run `ls -la` ora"))
check("sanitise unwraps links", fc.sanitise("see [docs](http://x) here") == "see docs here")
check("sanitise strips headers", fc.sanitise("## Titolo").startswith("Titolo"))
check("sanitise collapses whitespace", fc.sanitise("a\n\n  b   c") == "a. b c")
check("sanitise empty", fc.sanitise("") == "")

# --- spoken extraction ----------------------------------------------------------
lang, text = fc.extract_spoken('Blah <spoken lang="it">Fatto, tutto ok.</spoken>')
check("extract it tag", (lang, text) == ("it", "Fatto, tutto ok."))
lang, text = fc.extract_spoken('x <spoken lang=\'en\'>Done.</spoken>')
check("extract en single quotes", (lang, text) == ("en", "Done."))
lang, text = fc.extract_spoken("no tag here")
check("no tag", (lang, text) == (None, None))
lang, text = fc.extract_spoken('<spoken lang="en">one</spoken> mid <spoken lang="it">due</spoken>')
check("last tag wins", (lang, text) == ("it", "due"))
lang, text = fc.extract_spoken('<spoken lang="IT-IT">Ciao.</spoken>')
check("lang lowercased", lang == "it-it")

# --- voice mapping ----------------------------------------------------------------
vm = dict(fc.DEFAULT_VOICE_MAP)
check("voice it", fc.voice_for_lang("it", vm) == "it-IT-ElsaNeural")
check("voice it-IT", fc.voice_for_lang("it-IT", vm) == "it-IT-ElsaNeural")
check("voice en-US", fc.voice_for_lang("en-US", vm) == "en-US-AvaMultilingualNeural")
check("voice unknown falls to default", fc.voice_for_lang("xx", vm) == vm["default"])
check("voice empty falls to default", fc.voice_for_lang("", vm) == vm["default"])

# --- wake word pattern ---------------------------------------------------------------
ph.CONNECTORS = r"comunque|btw|anyway"  # freeze for tests
pattern = ph.wake_pattern("franco")
m = pattern.match("Comunque Franco, domani ho una riunione alle 3")
check("wake 'Comunque Franco,'", m and m.group(1).strip() == "domani ho una riunione alle 3")
m = pattern.match("comunque FRANCO prova")
check("wake lowercase caps mix", m and m.group(1).strip() == "prova")
m = pattern.match("btw franco nota a margine")
check("wake english connector", m and m.group(1).strip() == "nota a margine")
check("wake no match plain", pattern.match("fix the bug in parser.py") is None)
check("wake no match wake only", pattern.match("Comunque Franco") is None or pattern.match("Comunque Franco").group(1).strip() == "")
other = ph.wake_pattern("alfredo")
m = other.match("Comunque Alfredo, ricordati la scadenza")
check("wake custom name", m and m.group(1).strip() == "ricordati la scadenza")
check("wake other name no cross-match", pattern.match("Comunque Alfredo, x") is None)

# --- stop hook transcript parsing -------------------------------------------------------
with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
    json.dump({"type": "user", "message": {"role": "user", "content": "ciao"}}, f)
    f.write("\n")
    json.dump({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "Analizzo il file. <spoken lang=\"it\">Ho trovato il bug, correggo ora.</spoken>"}
    ]}}, f)
    f.write("\n")
    json.dump({"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "t1", "name": "Edit", "input": {}}
    ]}}, f)
    f.write("\n")
    transcript = f.name
text = sh.last_assistant_text(transcript, attempts=1)
check("transcript last text msg", 'Ho trovato il bug' in text)
lang, summary = fc.extract_spoken(text)
check("transcript spoken extracted", (lang, summary) == ("it", "Ho trovato il bug, correggo ora."))
os.unlink(transcript)

print()
if FAILURES:
    print("%d FAILED: %s" % (len(FAILURES), ", ".join(FAILURES)))
    sys.exit(1)
print("all tests passed")
