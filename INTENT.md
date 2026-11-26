# INTENT — claude-franco

> Visione in una riga: dare a Claude Code un **nome** e una **voce** — risposte riassunte a voce
> con voci neurali, barge-in automatico quando l'utente riprende la parola, e un nome di richiamo
> per aggiungere annotazioni a margine a metà task.

## Perché esiste

Claude Code ha dettatura vocale in input (`/voice`, push-to-talk) ma **nessun output vocale**.
Chi lavora a voce — con Wispr Flow o con la dettatura integrata — deve comunque leggere le
risposte sullo schermo. Esistono due progetti community (give-claude-code-voice-tts,
claude-speak), ciascuno con metà della soluzione: il primo ha voci neurali ma è Windows-only e
anglocentrico; il secondo è multipiattaforma ma usa motori robotici del sistema operativo.
Nessuno dei due ha un meccanismo di dialogo vero.

## Differenziatori (v1)

1. **Italiano e multilingua.** Voci curate per italiano (it-IT-ElsaNeural / it-IT-GiuseppeNeural)
   e mappa lingua→voce estendibile. La lingua non si "indovina": Claude stesso la dichiara nel
   tag `<spoken lang="it">…</spoken>`, perché sa già in che lingua sta scrivendo. Zero librerie
   di detection, zero falsi positivi.

2. **Barge-in automatico.** Quando l'utente invia un nuovo prompt, la riproduzione in corso si
   interrompe subito (hook UserPromptSubmit → demone). La differenza tra "un robot che legge" e
   "una conversazione". Nessun hotkey da ricordarsi.

3. **Nome di richiamo ("Comunque Franco…").** Mentre Claude esegue un task, l'utente può dire o
   scrivere `Comunque <nome>, <frase>` (o usare `/btw`). Lo hook rileva il pattern, inietta il
   contesto "annotazione a margine: conferma a voce in una riga e prosegui il task", e la
   conferma arriva **parlata** mentre il lavoro principale prosegue. Il nome è configurabile
   (default: Franco).

4. **Riassunto parlato, mai codice.** Claude chiude le risposte conversazionali con un breve
   paragrafeto in prosa dentro `<spoken>`. Tabelle, codice e dump di file non vengono mai letti
   (non ricevono il tag; sanitiser di sicurezza a valle).

## Architettura

```
utente parla/scrive ──▶ UserPromptSubmit hook ──▶ barge-in (silenzio demone)
                                        └─▶ wake word? ──▶ additionalContext "btw"
Claude risponde ──▶ tag <spoken> ──▶ Stop hook ──▶ demone locale (edge-tts caldo)
                                                        └─▶ sintesi + playback MCI
SessionStart hook ──▶ inietta regola <spoken> (se abilitato) + assicura demone attivo
```

- **Demone** HTTP su localhost, token-authenticated, demone caldo (no cold-start Python/TLS per
  ogni risposta), coda di riproduzione serializzata.
- **Config** in `~/.franco/` (enabled, mappa voci, wake word). **Off by default**, opt-in.
  Nell'alpha le impostazioni valgono per utente; quelle per progetto sono in roadmap.
- **Engine**: edge-tts (voci neurali Microsoft, gratuite, no account). Playback Windows via
  MCI/winmm.dll; il modulo playback è isolato per estendere macOS/Linux in v2.

## Non-obiettivi (v1)

- Lettura integrale delle risposte (possibile comando `/speak-full` in v2).
- Sintesi in streaming per frase e fallback offline SAPI/Piper (v2).
- Multipiattaforma completa (v2; la sintesi è già cross-platform, manca solo il playback).
- Hotkey globale di interrupt: il barge-in lo rende ridondante.

## Vincoli accettati

- edge-tts parla con un endpoint non documentato di Microsoft: può cambiare senza preavviso.
  Il testo del riassunto viaggia verso i server Microsoft; il suo contenuto dipende dal modello,
  quindi non è una garanzia di anonimizzazione. Documentato in SECURITY.md; i fallback offline
  (SAPI/Piper) sono pianificati per la v2.
- Il tag `<spoken>` dipende dall'istruzione iniettata a SessionStart: se il modello "dimentica",
  la risposta semplicemente non viene letta (degradazione silenziosa, mai rumorosa).

## Pubblico

Sviluppatori che lavorano a voce (dettatura/WhisperFlow), utenti con esigenze di accessibilità
o affaticamento visivo, chiunque voglia sentire "task completato" da dietro lo schermo.
Repo pubblico su GitHub, licenza MIT, README in inglese e in italiano.
