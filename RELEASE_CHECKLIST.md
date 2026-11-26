# Franco — modifiche necessarie prima del rilascio pubblico

## Obiettivo

Preparare una prima release **`v0.1.0-alpha.1`, Windows-only**, installabile seguendo
il README e con limiti dichiarati. Non è necessario completare la roadmap v2 per
pubblicare una buona alpha.

Questo documento è un piano di lavoro: le caselle aperte indicano interventi
ancora da eseguire, non funzionalità già disponibili.

## Stato rilevato durante la revisione

- I **26 controlli unitari** di `python tests/test_franco.py` passano.
- `claude plugin validate .`, eseguito con Claude Code **2.1.325**, fallisce per
  l'assenza del contenitore `hooks` in `hooks/hooks.json`.
- Sono stati riprodotti con prove isolate: coda audio senza limite effettivo,
  file temporanei residui dopo un errore di sintesi, estrazione di una risposta
  precedente dal transcript e limiti dei filtri sul testo parlato.
- Il percorso completo Claude Code → sintesi Microsoft → riproduzione Windows
  **non è stato verificato** durante la revisione; nel Python usato mancava
  `edge-tts`.
- Configurazione e demone sono condivisi in `~/.franco/`: non c'è isolamento
  esplicito per progetto o sessione.

## Avanzamento (26 novembre 2026, branch `release/v0.1.0-alpha.1`)

- P0 n. 1 completato: `claude plugin validate .` passa; gli hook sono stati
  osservati in sessioni reali con Claude Code 2.1.332 (`--plugin-dir`); con il
  riferimento esplicito nel manifest lo hook veniva comunque eseguito una sola
  volta, ma i percorsi standard sono stati rimossi dal manifest per chiarezza.
- P0 n. 2 quasi completato: `marketplace.json` aggiunto e installazione da
  marketplace locale verificata in una configurazione isolata; comandi esposti
  come `/franco:franco` e `/franco:btw` (il comando prevale sulla skill omonima).
  Resta la prova da checkout pulito con spazi nel percorso e quella da GitHub
  dopo il push.
- P0 n. 3 completato: nuovo launcher `hooks/run.sh`; scoperto e corretto anche
  un bug di encoding (stdin degli hook decodificato in cp1252).
- P0 n. 4: documentazione allineata (README, `SECURITY.md`); restano le
  modifiche al codice di estrazione e la politica sui tag malformati.
- P1 n. 6: lo Stop hook usa `last_assistant_message`; in sessione reale il testo
  finale arrivava nel transcript dopo l'esecuzione dello hook.
- P1 n. 7: aggiunto `franco_ctl.py stop` (endpoint `/shutdown` autenticato).
- P1 n. 9: `/franco:franco on` attiva la regola `<spoken>` anche nella sessione
  corrente.
- Seconda tornata (stesso giorno):
  - P0 n. 4 completato: i tag che iniziano dentro codice sono ignorati; i
    riassunti con codice, tabelle, markup o troppo lunghi non vengono letti.
  - P1 n. 5 completato: coda limitata con scarto atomico, nessuna riproduzione
    dopo `/silence`, file temporanei sempre rimossi, timeout di rete, salute
    di sintesi e riproduzione che si ripristina.
  - P1 n. 6 completato: ogni turno viene letto al massimo una volta.
  - P1 n. 7 completato: istanza singola con lock, stato atomico e validato,
    input HTTP validato. Trovato e corretto un reset di connessione su Windows
    quando il server rispondeva senza leggere il corpo. Il token sta in
    `%USERPROFILE%`, accessibile solo all'utente, a SYSTEM e agli amministratori.
  - Un demone avviato da una versione precedente del plugin viene sostituito
    automaticamente (impronta del codice in `/health`).
  - Voci: `it-IT-GiuseppeNeural` e `de-DE-KatjaNeural` non esistono più nel
    catalogo; lista curata rifatta con voce femminile e maschile per lingua.
  - Test: 133 controlli (unitari, demone simulato, integrazione hook), stabili su
    10 esecuzioni con Python 3.10 e 3.14; workflow GitHub Actions aggiunto.
  - Checkout pulito in un percorso con spazi: test, validazione, installazione da
    marketplace locale e sessione reale riusciti.
  - "Senza rete" verificato con errori di rete simulati, non scollegando la rete.
  - P1 n. 8: scelto il funzionamento globale per l'alpha (documentato); la voce
    sull'isolamento è quindi non applicabile.
- Restano aperti: annotazione durante un task reale lungo (serve una sessione
  interattiva), installazione da GitHub dopo il push, demo, punti P2.
- Percorso audio completo osservato (log del demone: `spoke … : ok`); in
  modalità `claude -p` l'audio viene interrotto da SessionEnd, limite documentato.

## Priorità

| Livello | Significato |
| --- | --- |
| P0 | Da risolvere prima di annunciare una release installabile. |
| P1 | Affidabilità da consolidare prima dell'alpha, oppure limite da dichiarare quando indicato. |
| P2 | Miglioramenti successivi, non bloccanti per l'alpha. |

## P0 — integrazione e installazione

### 1. Correggere e validare gli hook

**File:** `hooks/hooks.json`, `.claude-plugin/plugin.json`.

- [x] Racchiudere gli eventi di `hooks/hooks.json` in una proprietà principale
  `"hooks"`, come richiesto dal formato dei file hook.
- [x] Verificare se mantenere il riferimento esplicito al file nel manifest,
  dato che `hooks/hooks.json` è già una posizione standard; evitare che la
  configurazione venga applicata due volte.
- [x] Eseguire `claude plugin validate .` e correggere tutti gli errori.
- [x] Verificare in una vera sessione che ogni hook venga eseguito una sola volta.

**Accettazione:** validazione riuscita; gli eventi `SessionStart`,
`UserPromptSubmit`, `Stop` e `SessionEnd` funzionano nel plugin caricato.

### 2. Rendere riproducibile l'installazione

**File:** `README.md`, `.claude-plugin/`, `commands/franco.md`,
`skills/franco/SKILL.md`.

- [x] Scegliere il percorso di distribuzione: marketplace del repository oppure
  caricamento locale con `--plugin-dir` per l'anteprima.
- [x] Se si mantiene il percorso marketplace descritto nel README, aggiungere
  `.claude-plugin/marketplace.json` con una voce che punti al plugin.
- [x] Documentare clonazione, installazione delle dipendenze, registrazione del
  marketplace e installazione del plugin, nell'ordine corretto.
- [x] Sostituire nei contenuti Markdown `$CLAUDE_PLUGIN_ROOT` con
  `${CLAUDE_PLUGIN_ROOT}`, la forma di sostituzione documentata da Claude Code.
- [x] Verificare i nomi effettivamente esposti e documentare i comandi con
  namespace, ad esempio `/franco:franco on` e `/franco:btw`.
- [x] Verificare la coesistenza della skill `franco` e del comando `franco`;
  consolidarli o rinominarli se l'esposizione risulta ambigua.
- [x] Dichiarare la versione minima di Claude Code effettivamente collaudata.
- [x] Provare tutto da un checkout pulito, possibilmente con spazi nel percorso.

**Accettazione:** un utente può ottenere la prima risposta parlata seguendo
soltanto il README, senza modifiche manuali non documentate.

### 3. Dichiarare le dipendenze e verificare l'interprete

**File:** nuovo `requirements.txt` oppure `pyproject.toml`, `README.md`,
`hooks/franco_common.py`.

- [x] Dichiarare `edge-tts` con una versione o un intervallo collaudato.
- [x] Documentare l'installazione con `python -m pip`, evitando ambiguità tra
  `pip` e l'interprete che esegue gli hook.
- [x] Verificare che il `pythonw` usato per il demone appartenga allo stesso
  ambiente Python degli hook; non affidarsi soltanto al primo trovato nel PATH.
- [x] Segnalare chiaramente dipendenza mancante e avvio del demone fallito.
- [x] Collaudare almeno Python 3.10 e una versione recente se si mantiene la
  dichiarazione di supporto a Python 3.10+.

**Accettazione:** la configurazione funziona su Windows con l'interprete
documentato; un'installazione incompleta produce un errore utile, non solo silenzio.

## P0 — privacy e accuratezza delle promesse

### 4. Correggere documentazione e trattamento del testo

**File:** `README.md`, `INTENT.md`, nuovo `SECURITY.md`,
`hooks/franco_common.py`, `hooks/session_start.py`, `tests/`.

Problemi verificati:

- `sanitise()` rimuove i delimitatori del codice inline, ma ne conserva il testo.
- I separatori delle tabelle vengono rimossi, ma i dati restano nel risultato.
- `extract_spoken()` riconosce un tag anche all'interno di un blocco di codice.

- [x] Rimuovere le garanzie assolute secondo cui codice e dati sensibili non
  possono mai essere inviati a Microsoft.
- [x] Spiegare che viene inviato il riassunto selezionato e che il suo contenuto
  dipende anche dal modello: non è una garanzia di anonimizzazione.
- [x] Escludere dall'estrazione i tag presenti in blocchi di codice e collaudare
  il caso con test di regressione.
- [x] Definire una politica conservativa per codice, tabelle e tag malformati:
  se il contenuto non è adatto alla lettura, preferire di non pronunciarlo.
- [x] Non presentare il sanitizzatore come un filtro completo di segreti.
- [x] Documentare servizio esterno, necessità di Internet, endpoint non
  ufficialmente supportato, dati locali e modalità di disattivazione.
- [x] Distinguere le alternative offline pianificate da quelle già implementate;
  correggere il riferimento ai fallback documentati se non sono ancora descritti.

**Accettazione:** documentazione e comportamento coincidono; gli esempi di codice
non vengono interpretati come istruzioni di sintesi. Il rischio residuo sul
contenuto dei riassunti è dichiarato prima dell'attivazione.

## P1 — affidabilità del servizio audio

### 5. Correggere coda, interruzione e file temporanei

**File:** `hooks/franco_daemon.py`, `hooks/playback.py`, `tests/`.

- [x] Applicare il limite previsto creando una coda con `maxsize=MAX_QUEUE`.
- [x] Rendere sicura la politica di sostituzione dell'elemento più vecchio anche
  in presenza di richieste concorrenti, senza bloccare gli handler HTTP.
- [x] Eliminare il file temporaneo anche se la sintesi solleva un'eccezione.
- [x] Testare l'interruzione durante sintesi, riproduzione e passaggio dalla coda
  al worker, evitando riproduzioni tardive dopo `/silence`.
- [x] Verificare timeout e recupero dopo errori di rete del servizio TTS.
- [x] Rendere visibili gli errori di playback: attualmente alcuni fallimenti MCI
  restituiscono `False`, risultato che il chiamante non segnala.
- [x] Aggiornare correttamente lo stato di salute dopo un errore e dopo il
  successivo recupero.

**Accettazione:** la coda resta limitata, l'audio interrotto non riparte e gli
errori non lasciano file temporanei né un servizio apparentemente sano ma muto.

### 6. Leggere soltanto la risposta del turno corrente

**File:** `hooks/stop_hook.py`, `tests/`.

- [x] Evitare che la ricerca dell'ultimo testo assistant risalga a una risposta
  precedente all'ultimo messaggio utente.
- [x] Verificare il payload `Stop` della versione supportata e valutare l'uso
  del messaggio finale fornito dall'evento, se disponibile.
- [x] Gestire transcript incompleti, righe malformate e messaggi con soli tool.
- [x] Aggiungere una protezione contro la lettura duplicata dello stesso turno.

**Accettazione:** nessuna risposta precedente viene riletta quando il turno
corrente non contiene un nuovo riassunto valido.

### 7. Gestire avvio, stato e arresto del demone

**File:** `hooks/franco_common.py`, `hooks/franco_daemon.py`,
`hooks/franco_ctl.py`.

Questi punti sono rischi da verificare e consolidare, non tutti bug già riprodotti.

- [x] Proteggere l'avvio simultaneo da più hook o sessioni con un meccanismo
  single-instance.
- [x] Scrivere lo stato in modo atomico e gestire stato obsoleto o malformato.
- [x] Verificare le autorizzazioni della cartella e del file contenente il token.
- [x] Validare il tipo del JSON e gli header HTTP senza eccezioni non gestite.
- [x] Propagare gli errori nella CLI: `enable` e `preview` non devono indicare
  successo quando avvio o invio falliscono.
- [x] Documentare come arrestare il demone e rimuovere la configurazione;
  chiarire che `disable` silenzia ma non termina il processo.

**Accettazione:** avvii concorrenti non producono demoni incontrollati; status e
messaggi della CLI descrivono lo stato effettivo.

## P1 — comportamento e limiti da scegliere

### 8. Decidere lo scope di configurazione e sessioni

**File:** `hooks/franco_common.py`, `hooks/prompt_hook.py`,
`hooks/session_end.py`, `README.md`, `INTENT.md`.

- [x] Scegliere tra isolamento per progetto/sessione e funzionamento globale.
- [x] Se si implementa l'isolamento, evitare che prompt e chiusura di una
  sessione interrompano l'audio di un'altra.
- [x] Se si mantiene il comportamento globale nell'alpha, documentare
  esplicitamente il limite e rimuovere la promessa di opt-in per progetto.
- [x] Preservare `FRANCO_HOME` come override utile per test isolati.

**Accettazione:** il comportamento con due sessioni aperte è collaudato e
corrisponde alla documentazione, oppure è dichiarato non supportato nell'alpha.

### 9. Chiarire attivazione, wake name e annotazioni

**File:** `hooks/session_start.py`, `hooks/prompt_hook.py`,
`commands/franco.md`, `commands/btw.md`, `skills/franco/SKILL.md`, `README.md`.

- [x] Verificare che l'attivazione a sessione già iniziata fornisca anche la
  regola per generare i riassunti, non soltanto l'avvio del demone.
- [x] Se serve una nuova sessione, dichiararlo coerentemente in comando, skill
  e README; l'avvio del demone da solo non inietta la regola nel contesto.
- [x] Spiegare che il wake name viene riconosciuto nel testo inviato, non da un
  microfono ascoltato direttamente dal plugin.
- [x] Descrivere il barge-in come interruzione all'invio del prompt, non al primo
  suono pronunciato dall'utente.
- [x] Distinguere il comando del plugin dal `/btw` nativo di Claude Code.
- [ ] Collaudare un'annotazione durante un task reale: una semplice istruzione
  aggiunta al prompt non dimostra l'esistenza di un canale indipendente.
- [ ] Se la gestione davvero indipendente non è disponibile, ridimensionare la
  promessa per l'alpha invece di presentarla come equivalente al `/btw` nativo.

**Accettazione:** ogni funzione pubblicizzata è stata osservata in una sessione
reale; ciò che dipende dal comportamento del modello è descritto come tale.

## Verifiche minime prima della release

- [x] Aggiungere GitHub Actions su Windows con test Python e validazione del plugin.
- [x] Aggiungere test di integrazione degli hook con stdin JSON e ambiente isolato.
- [x] Testare il servizio HTTP con TTS e playback simulati: token errato, payload
  non valido, coda piena, silenzio ed errori di sintesi.
- [x] Eseguire i test di regressione per i problemi elencati in questo documento.
- [x] Eseguire un collaudo manuale con sintesi e audio reali, usando soltanto
  testo di prova non sensibile.
- [x] Verificare lingua italiana e inglese, cambio voce, nome personalizzato,
  attivazione/disattivazione e riavvio di Claude Code.
- [x] Verificare il comportamento senza rete e con `edge-tts` mancante.
- [ ] Ripetere l'installazione documentata da un checkout pulito.

## Materiale per GitHub

- [x] Aggiungere `SECURITY.md` con privacy e istruzioni per segnalare vulnerabilità.
- [x] Aggiungere `CHANGELOG.md` e note della prima alpha con limiti noti.
- [x] Aggiungere al README una sezione troubleshooting e istruzioni di rimozione.
- [x] Inserire nel manifest URL reali del repository e del supporto, una volta
  deciso dove pubblicare; non lasciare URL segnaposto nella release.
- [x] Verificare che i file pubblicati non contengano credenziali, log,
  configurazione personale o audio generato.
- [ ] Preparare una breve demo con testo non sensibile.

## P2 — non bloccante per la prima alpha

- [ ] `CONTRIBUTING.md` e template per issue e pull request.
- [ ] Comando diagnostico, ad esempio `doctor`, per interprete, dipendenze,
  demone, rete e backend audio.
- [ ] Icona del progetto; diventa rilevante per la candidatura al catalogo
  Anthropic, ma non è necessaria per pubblicare il sorgente su GitHub.
- [ ] Supporto macOS/Linux con backend audio reali.
- [ ] Sintesi in streaming e fallback offline SAPI/Piper.

## Criterio finale di rilascio

Pubblicare l'alpha quando:

1. Tutti i P0 sono completati.
2. I problemi P1 riprodotti sono corretti; i limiti di scope e comportamento
   mantenuti intenzionalmente sono espliciti nelle note di rilascio.
3. Test automatici e validazione passano.
4. Installazione pulita e percorso audio completo sono stati verificati.
5. README, manifest e comportamento reale non si contraddicono.

Non presentare questa prima versione come stabile né come filtro di sicurezza
per il contenuto delle conversazioni.
