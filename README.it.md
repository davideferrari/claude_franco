<div align="center">

# 🎙️ Franco

**Dai un nome e una voce a Claude Code.**

Franco risponde a voce. Voci neurali riassumono a parlato ogni risposta, la
riproduzione si interrompe nell'istante in cui riprendi la parola, e puoi
chiamare Claude per nome per aggiungere una nota a metà task senza farlo
deragliare.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Versione](https://img.shields.io/badge/versione-0.1.0-blue.svg)]()
[![Piattaforma](https://img.shields.io/badge/piattaforma-Windows%2010%2F11-0078D6.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)]()
[![Claude Code](https://img.shields.io/badge/per-Claude%20Code-d97757.svg)]()

*Italiano per prima, multilingua · Voci neurali gratuite · Zero account*

[🇬🇧 English](README.md) · **🇮🇹 Italiano**

</div>

---

> Claude Code ha già la **dettatura vocale** in input (`/voice`), ma nulla
> risponde a voce. Abbina la tua dettatura (quella integrata, o WhisperFlow) a
> Franco e ottieni una vera **conversazione a due nel terminale**.
>
> <!-- TODO: aggiungere una GIF demo qui prima della pubblicazione -->

## ✨ In breve

|  | Funzionalità | Cosa significa |
|---|--------------|----------------|
| 🔊 | **Riassunti parlati** | Claude chiude le risposte conversazionali con un breve riassunto in prosa, pronunciato da una voce neurale. Codice, tabelle e dump di file **non vengono mai letti** — per design non ricevono il tag. |
| 🇮🇹 | **Italiano per prima, multilingua** | Voci curate per italiano (`it-IT-ElsaNeural`, `it-IT-GiuseppeNeural`), altre lingue dietro una mappa `lingua → voce`. È Claude stesso a dichiarare la lingua (`<spoken lang="it">`) — nessuna libreria di detection, nessun falso positivo. |
| ⚡ | **Barge-in** | Inviare un nuovo prompt interrompe l'audio all'istante. Riprendere la parola *è* l'interruzione — nessun hotkey da ricordarsi. |
| 🙋 | **Nome di richiamo** | Mentre Claude lavora, dici o scrivi `Comunque Franco, <nota>`. Lo riconosce ad alta voce in una riga e prosegue il lavoro. Disponibile anche come `/btw <nota>`. |
| 🔥 | **Demone caldo** | Un demone localhost autenticato via token sintetizza e riproduce — nessun cold-start Python/TLS a ogni risposta. |
| 🔓 | **Gratuito e senza account** | Voci neurali Microsoft Edge via `edge-tts`. Nessun abbonamento, nessuna API key, nessun account. |

## 📦 Installazione

Franco è un plugin per [Claude Code](https://claude.com/claude-code).

**Da checkout locale:**

```jsonc
// ~/.claude/settings.json
{
  "extraKnownMarketplaces": {
    "franco": {
      "source": { "source": "directory", "path": "/percorso/assoluto/verso/claude-franco" }
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

**Requisiti**

- Windows 10/11 (la riproduzione usa MCI; macOS/Linux previsto per la v2)
- Python 3.10+ nel PATH
- `pip install edge-tts` — TTS neurale gratuito; la sintesi è una chiamata di
  rete, quindi serve internet

## 🚀 Quick start

```text
/franco on          # attiva la voce (avvia anche il demone)
/franco voice       # sfoglia e scegli una voce
/franco wakeword    # scegli il nome a cui Claude risponde
/franco off         # silenzia
```

Oppure con la CLI:

```bash
python hooks/franco_ctl.py enable
python hooks/franco_ctl.py status
python hooks/franco_ctl.py set-wakeword "Alfredo"
python hooks/franco_ctl.py silence
```

## ⚙️ Come funziona

```
utente parla/scrive ──▶ hook UserPromptSubmit ──▶ barge-in (il demone tace)
                                         └─▶ wake word? ──▶ nota a margine "btw"
Claude risponde ──▶ tag <spoken> ──▶ hook Stop ──▶ demone locale caldo
                                                        └─▶ edge-tts + playback MCI
hook SessionStart ──▶ inietta la regola <spoken> (se abilitato) + assicura il demone
```

1. Un **hook SessionStart** inietta la regola di emissione `<spoken>` (solo
   dove la voce è abilitata) e si assicura che il demone sia attivo.
2. Claude chiude le risposte conversazionali con
   `<spoken lang="xx">…</spoken>` (prosa semplice, 1–2 frasi, niente markdown).
3. L'**hook Stop** estrae il tag dalla trascrizione e lo invia via POST al
   demone, che lo sintetizza con la voce mappata alla lingua e lo riproduce
   (MCI su Windows).
4. L'**hook UserPromptSubmit** realizza la sensazione di conversazione:
   barge-in a ogni nuovo prompt, e il rilevamento del nome di richiamo
   trasforma `Comunque Franco, …` in una nota a margine a metà task (stesso
   comportamento di `/btw`).

La voce è **spenta di default** e opt-in. Le risposte ricche di dati (codice,
tabelle, dump) restano silenziose per design — se il modello "dimentica" il
tag, la risposta semplicemente non viene letta: degradazione silenziosa, mai
rumorosa.

## 🔒 Privacy e sicurezza

- Il tuo **codice, le tabelle e i dump di file non vengono mai inviati
  da nessuna parte**: non ricevono mai un tag `<spoken>`. Dalla tua macchina
  esce solo il breve riassunto in prosa.
- Il riassunto viene sintetizzato dal backend `edge-tts` di Microsoft (il
  servizio non documentato dietro Read Aloud di Edge — gratuito, senza
  account, ma non un'API supportata; può cambiare senza preavviso). I fallback
  sono documentati in [`INTENT.md`](INTENT.md).
- Il demone ascolta solo su `127.0.0.1` ed è autenticato via token.

## 🗺️ Roadmap

Consegnato in **v0.1.0** — l'intero loop vocale end-to-end.

Previsto per la **v2**:

- [ ] Riproduzione su macOS/Linux (la sintesi è già cross-platform)
- [ ] Sintesi in streaming, frase per frase
- [ ] Fallback offline (SAPI / Piper)
- [ ] `/speak-full` — leggere l'intera risposta ad alta voce

## 🤝 Contributi

Aperto a chiunque — issue, PR e nuove voci per la mappa `lingua → voce` sono
benvenute. Manteniamolo amichevole.

## 📄 Licenza

Rilasciato sotto [Licenza MIT](LICENSE) — **libero di usare, modificare e
condividere, per chiunque**. Vale per te, il tuo team, il tuo progetto
parallelo e la tua azienda.

<div align="center">

*Costruito per chi parla al terminale.*

</div>
