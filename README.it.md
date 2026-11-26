<div align="center">

# Franco

### Una voce per Claude Code

Franco legge ad alta voce, con voci neurali naturali, un breve riassunto di
ogni risposta di Claude Code. Interrompe l'audio non appena invii il prompt
successivo e ti permette di chiamare Claude per nome per aggiungere una nota
senza fermarne il lavoro.

[![Licenza: MIT](https://img.shields.io/badge/licenza-MIT-yellow.svg)](LICENSE)
[![Release](https://img.shields.io/badge/release-0.1.0--alpha.1-orange.svg)](CHANGELOG.md)
[![Piattaforma](https://img.shields.io/badge/piattaforma-Windows%2010%20%7C%2011-0078D6.svg)](#requisiti)
[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB.svg)](#requisiti)
[![Plugin Claude Code](https://img.shields.io/badge/Claude%20Code-plugin-D97757.svg)](https://claude.com/claude-code)

[English](README.md) · **Italiano**

</div>

<!-- Demo: aggiungere qui una breve registrazione dello schermo con audio prima dell'annuncio. -->

---

## Perché Franco

Claude Code accetta già l'input vocale, con la dettatura integrata o con
strumenti come Wispr Flow, ma le sue risposte sono solo testo. Se lavori a
voce, ti allontani dallo schermo o vuoi semplicemente sentire "fatto" mentre
guardi altro, devi comunque leggere ogni risposta.

Franco chiude il cerchio. Alla fine di ogni risposta conversazionale Claude
scrive un riassunto di una o due frasi pensato per l'ascolto, e Franco lo
pronuncia. Codice, tabelle e diff non vengono letti.

## Funzionalità

| | |
|---|---|
| **Riassunti parlati** | Claude chiude le risposte conversazionali con un breve riassunto in prosa dentro un tag `<spoken>`, che Franco legge ad alta voce. Le risposte composte soprattutto da codice, tabelle o contenuti di file non ricevono il riassunto e restano silenziose. |
| **Italiano prima di tutto, multilingua** | Voci femminili e maschili selezionate per italiano, inglese, spagnolo, francese, tedesco e portoghese, e oltre 300 nel catalogo completo. È Claude a dichiarare la lingua di ogni riassunto (`<spoken lang="it">`): nessun rilevamento automatico. |
| **Interruzione immediata** | Inviare un nuovo prompt ferma subito l'audio in corso. Nessuna scorciatoia da ricordare. |
| **Nome di richiamo** | Inizia un messaggio con `Comunque Franco, …` per aggiungere una nota: Claude la conferma con una frase parlata e prosegue il lavoro. Il nome è configurabile. `/franco:btw <nota>` fa lo stesso. |
| **Servizio locale sempre pronto** | Un piccolo processo in background su `127.0.0.1`, protetto da un token rigenerato a ogni avvio, sintetizza e riproduce l'audio senza i ritardi di avvio di Python. |
| **Gratuito, senza account** | Le voci arrivano dalla sintesi vocale neurale online di Microsoft tramite la libreria open source [`edge-tts`](https://github.com/rany2/edge-tts). Nessuna API key, nessun abbonamento. |

## Requisiti

- **Windows 10 o 11.** La riproduzione usa la Media Control Interface di
  Windows. macOS e Linux sono nella roadmap.
- **Claude Code** con supporto ai plugin. Collaudato con la versione 2.1.332.
- **Python 3.10 o successivo**, da [python.org](https://www.python.org/downloads/windows/)
  (consigliato: include il launcher `py`) o da qualsiasi altra distribuzione.
  Collaudato end to end con la 3.14; la suite di test gira anche sulla 3.10.
- **Una connessione a Internet** mentre la voce è attiva: la sintesi è un
  servizio online.

## Installazione

**1. Aggiungi il marketplace e installa il plugin**

```bash
claude plugin marketplace add davideferrari/claude_franco
claude plugin install franco@claude-franco
```

Le stesse operazioni sono disponibili in Claude Code con `/plugin`. Per
provare un checkout locale senza installarlo, avvia Claude Code con
`claude --plugin-dir <percorso-del-checkout>`.

**2. Installa la libreria vocale nel Python che userà Franco**

```powershell
py -3 -m pip install "edge-tts>=7.0,<8"
```

Franco cerca Python in quest'ordine: la variabile d'ambiente `FRANCO_PYTHON`,
`py -3`, `python3`, `python`. I segnaposto del Microsoft Store ("Alias di
esecuzione dell'app") vengono riconosciuti e scartati. Se usi un ambiente
virtuale o un interprete specifico, imposta `FRANCO_PYTHON` sul relativo
`python.exe`.

**3. Attiva la voce**

In Claude Code:

```text
/franco:franco on
```

Franco verifica la dipendenza, avvia il servizio in background e conferma. Se
manca qualcosa, indica il comando esatto da eseguire. La voce si attiva
subito nella sessione corrente e in tutte le sessioni successive.

## Utilizzo

| Comando | Cosa fa |
|---|---|
| `/franco:franco` | Mostra lo stato: voce, nome di richiamo, voci, servizio, Python, `edge-tts` |
| `/franco:franco on` · `off` | Attiva o disattiva la voce |
| `/franco:franco silence` | Ferma l'audio in corso; la voce resta attiva |
| `/franco:franco stop` | Arresta il servizio in background; riparte con la sessione successiva se la voce è attiva |
| `/franco:franco voice` | Sceglie una voce per lingua, con un ascolto di prova prima di confermare |
| `/franco:franco wakeword` | Cambia il nome a cui risponde Claude (predefinito: Franco) |
| `/franco:btw <nota>` | Aggiunge una nota mentre Claude lavora |

Puoi anche chiedere in linguaggio naturale ("silenzio", "usa una voce
maschile italiana", "chiamati Alfredo"): la skill `franco` inclusa traduce la
richiesta nell'impostazione giusta.

> Claude Code ha anche un proprio `/btw` integrato per le domande veloci.
> La variante di Franco si chiama `/franco:btw` e conferma la nota a voce.

Gli stessi controlli sono disponibili da terminale, dalla cartella del plugin:

```bash
bash hooks/run.sh franco_ctl.py status
bash hooks/run.sh franco_ctl.py set-voice it it-IT-DiegoNeural
bash hooks/run.sh franco_ctl.py preview --lang it "Ciao, sono Franco."
```

## Voci

Ogni lingua ha la sua voce: Claude indica la lingua di ogni riassunto e
Franco usa la voce che hai scelto per quella lingua. Le voci selezionate:

| Lingua | Femminile | Maschile |
|---|---|---|
| Italiano | `it-IT-ElsaNeural` (predefinita), `it-IT-IsabellaNeural` | `it-IT-DiegoNeural`, `it-IT-GiuseppeMultilingualNeural` |
| Inglese | `en-US-AvaMultilingualNeural` (predefinita), `en-GB-SoniaNeural` | `en-US-AndrewMultilingualNeural`, `en-GB-RyanNeural` |
| Spagnolo | `es-ES-ElviraNeural` | `es-ES-AlvaroNeural` |
| Francese | `fr-FR-DeniseNeural` | `fr-FR-HenriNeural` |
| Tedesco | `de-DE-TanjaNeural` | `de-DE-ChristophNeural` |
| Portoghese (Brasile) | `pt-BR-FranciscaNeural` | `pt-BR-AntonioNeural` |

`/franco:franco voice` ti guida nella scelta e ti fa ascoltare un esempio
prima di confermare. Oppure chiedi semplicemente: "usa una voce maschile
italiana". Per altri accenti e altre lingue puoi sfogliare il catalogo
completo del servizio vocale:

```bash
bash hooks/run.sh franco_ctl.py voices --all en-GB
bash hooks/run.sh franco_ctl.py preview --voice en-GB-ThomasNeural "Hello, I am Franco."
bash hooks/run.sh franco_ctl.py set-voice en en-GB-ThomasNeural
```

`set-voice` verifica l'identificativo sul catalogo: un errore di battitura o
una voce ritirata vengono segnalati invece di fallire in silenzio. Le lingue
senza una voce propria usano la voce `default` (`set-voice default <voice-id>`).

## Come funziona

```text
Invii un prompt ──▶ hook UserPromptSubmit ──▶ ferma l'audio in corso
                                       └──▶ nome di richiamo? ──▶ contesto "nota"
Claude risponde ──▶ tag <spoken lang="…"> ──▶ hook Stop ──▶ servizio locale
                                                               ├─ sintesi edge-tts
                                                               └─ riproduzione Windows
Avvio sessione ──▶ hook SessionStart ──▶ regola <spoken> + avvio del servizio
```

1. Con la voce attiva, lo hook **SessionStart** aggiunge al contesto di Claude
   una breve istruzione: chiudere le risposte conversazionali con un
   riassunto `<spoken>` in prosa semplice, e ometterlo per le risposte fatte
   di dati.
2. Lo hook **Stop** prende la risposta finale del turno, estrae l'ultimo tag
   `<spoken>` e lo passa al servizio locale.
3. Il servizio sintetizza il testo con la voce associata alla lingua
   dichiarata e lo riproduce. La riproduzione è sequenziale e la coda è
   corta, quindi la voce non resta mai molto indietro.
4. Lo hook **UserPromptSubmit** ferma l'audio a ogni prompt inviato e
   riconosce il nome di richiamo.

Con la voce disattivata, gli hook terminano subito senza avviare Python.
Per ogni utente gira un solo servizio; dopo un aggiornamento del plugin, un
servizio ancora attivo con la versione precedente viene sostituito
automaticamente.

## Configurazione

Le impostazioni sono semplici file in `%USERPROFILE%\.franco\`, gestiti dai
comandi descritti sopra:

| File | Scopo |
|---|---|
| `enabled` | Presente quando la voce è attiva |
| `wakeword` | Il nome di richiamo |
| `voice_map.json` | Lingua → voce, ad esempio `{"it": "it-IT-ElsaNeural", "default": "en-US-AvaMultilingualNeural"}` |
| `python` | L'interprete trovato da Franco; eliminalo per ripetere la ricerca |
| `daemon.state`, `daemon.lock`, `daemon.log` | Porta e token del servizio, lock di istanza singola, log |
| `last_spoken` | Hash dell'ultimo riassunto, perché un turno non venga mai letto due volte |

| Variabile d'ambiente | Scopo |
|---|---|
| `FRANCO_PYTHON` | Percorso completo dell'interprete Python da usare |
| `FRANCO_HOME` | Cartella alternativa per le impostazioni, utile per i test |

## Privacy e dati

Leggi questa sezione prima di attivare la voce.

- **Cosa esce dal tuo computer:** solo il testo dentro ogni tag `<spoken>`,
  inviato al servizio vocale di Microsoft (`speech.platform.bing.com`) per la
  sintesi. Franco non invia i tuoi prompt, i tuoi file né il resto delle
  risposte.
- **Il riassunto lo scrive il modello.** Claude è istruito a usare prosa
  semplice senza codice, comandi o numeri lunghi, ma Franco non può garantire
  cosa contenga un riassunto. La pulizia del testo rimuove solo la
  formattazione: **non** è un filtro per segreti o dati personali. Come
  ulteriore cautela, un riassunto che contiene codice, una tabella o markup,
  o che è insolitamente lungo, non viene letto affatto, e i tag mostrati
  dentro blocchi di codice vengono ignorati. Se lavori
  con materiale riservato, tieni la voce disattivata in quella sessione.
- **Servizio non ufficiale.** `edge-tts` usa l'endpoint della funzione
  "Leggi ad alta voce" di Microsoft Edge. È gratuito e non richiede account,
  ma non è un'API pubblica supportata e può cambiare o smettere di funzionare
  senza preavviso.
- **Cosa resta in locale:** impostazioni e un log in `%USERPROFILE%\.franco\`.
  Il log registra lingua, voce, lunghezza ed esito di ogni frase, mai il
  testo. I file audio sono temporanei e vengono eliminati dopo la
  riproduzione.
- **Servizio locale:** ascolta solo su `127.0.0.1`. Ogni comando richiede un
  token casuale rigenerato a ogni avvio.

Dettagli e modalità di segnalazione delle vulnerabilità sono in
[SECURITY.md](SECURITY.md).

## Limiti noti

Franco è una release **alpha**:

- **Solo Windows**, per ora.
- **Le impostazioni valgono per utente, non per progetto.** Attivazione, voci
  e nome di richiamo si applicano a tutte le sessioni di Claude Code. Con due
  sessioni aperte, un prompt inviato in una ferma anche l'audio dell'altra.
- **Il nome di richiamo viene riconosciuto nel testo inviato**, scritto o
  dettato. Franco non ascolta il microfono.
- **L'interruzione avviene all'invio del prompt**, non quando inizi a parlare.
- **I riassunti dipendono dal modello**, che deve seguire l'istruzione. Se
  omette il tag, la risposta semplicemente non viene letta.
- **Le esecuzioni non interattive (`claude -p`) non vengono lette:** la
  sessione termina, e il suo audio viene fermato, subito dopo la risposta.

## Risoluzione dei problemi

| Sintomo | Cosa fare |
|---|---|
| "no working Python 3.10+ found" all'avvio della sessione | Installa Python da python.org, oppure imposta `FRANCO_PYTHON` sul `python.exe` del tuo interprete. |
| "edge-tts is not installed for …" | Esegui il comando indicato nel messaggio: installa la libreria nell'interprete usato da Franco. |
| Non viene letto nulla | Esegui `/franco:franco` e verifica che la voce sia attiva e il servizio in esecuzione, poi consulta `%USERPROFILE%\.franco\daemon.log`. Vengono lette solo le risposte che contengono un riassunto. |
| Python sbagliato dopo averne installato uno nuovo | Elimina `%USERPROFILE%\.franco\python`, oppure imposta `FRANCO_PYTHON`. |

## Disinstallazione

In Claude Code esegui `/franco:franco off` e poi `/franco:franco stop`.
Quindi, da terminale:

```bash
claude plugin uninstall franco@claude-franco
claude plugin marketplace remove claude-franco
```

Infine elimina `%USERPROFILE%\.franco\` per rimuovere impostazioni e log, e se
vuoi esegui `py -3 -m pip uninstall edge-tts`.

## Roadmap

- Riproduzione su macOS e Linux (la sintesi è già multipiattaforma)
- Sintesi in streaming, frase per frase
- Voci offline (Windows SAPI, Piper) come alternativa al servizio online
- Impostazioni per progetto
- `/speak-full` per leggere un'intera risposta

## Contribuire

Issue e pull request sono benvenute, anche per aggiungere voci alla mappa
delle lingue. Segnala i problemi di sicurezza in privato, come descritto in
[SECURITY.md](SECURITY.md). Prima di aprire una pull request esegui i
controlli:

```bash
py -3 tests/run_all.py
claude plugin validate .
```

## Ringraziamenti

Sintesi vocale a cura di [`edge-tts`](https://github.com/rany2/edge-tts).
Franco è un progetto indipendente, non affiliato né approvato da Anthropic o
Microsoft.

## Licenza

[MIT](LICENSE) © 2026 Davide Ferrari
