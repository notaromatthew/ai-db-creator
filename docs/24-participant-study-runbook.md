# Runbook operativo del pilot e dello studio RQ0/RQ3/RQ4

Stato: materiali tecnici pronti; raccolta con persone non ancora eseguita.

Questo runbook traduce il protocollo nei controlli che il coordinatore deve
eseguire. Non sostituisce il consenso informato e non autorizza la creazione di
dati sintetici da presentare come dati di partecipanti.

## 1. Prerequisiti documentali

Prima del pilot, il coordinatore deve:

1. archiviare l'evidenza scritta della determinazione istituzionale comunicata,
   secondo cui non è richiesta approvazione etica preventiva per questo studio;
2. verificare il testo di consenso e i contatti per ritiro/cancellazione;
3. confermare che il flusso non somministri NASA-TLX o SUS;
4. approvare un'unica versione delle istruzioni per i tre bracci `manual`,
   `ai_only` e `ai_interface` (quest'ultimo è denominato AI+UI nel paper);
5. verificare che i criteri di inclusione escludano chi ha formazione formale o
   esperienza professionale nei database;
6. definire chi conserva la tabella separata fra contatti e ID pseudonimi, se
   necessaria. Questa tabella non deve entrare negli export analitici.

## 2. Verifica tecnica pre-pilot

Eseguire su un ambiente pulito:

1. avvio completo di database, Redis, backend, frontend e gateway;
2. creazione di un account di prova per ciascun braccio;
3. percorso completo `consent -> demographics -> task -> debrief -> done`;
4. verifica dell'assegnazione casuale stratificata e dell'impossibilità di
   cambiare braccio dopo l'assegnazione;
5. verifica dei log di interazione, senza contenuto sensibile non necessario;
6. verifica degli export pseudonimi descritti in `docs/19-user-study-analysis.md`;
7. prova del ritiro e della cancellazione secondo `docs/13-data-governance.md`;
8. salvataggio di revisione Git, configurazione, hash dei dataset e versione
   delle istruzioni.

I record tecnici di prova devono essere marcati e rimossi prima del pilot.

## 3. Pilot formativo

Reclutare 5-8 persone idonee. I dati del pilot non entrano nell'analisi
confermativa.

Per ogni sessione:

1. assegnare un ID pseudonimo;
2. acquisire il consenso;
3. completare lo screening senza raccogliere dati eccedenti;
4. assegnare automaticamente braccio e dataset;
5. leggere le istruzioni standardizzate senza suggerimenti aggiuntivi;
6. svolgere il task e registrare esito, errori residui e tempo;
7. raccogliere nel debrief solo feedback facoltativo filtrato per privacy;
8. registrare problemi tecnici o di comprensione nel log del pilot.

Il log del pilot deve contenere almeno: ID problema, severità, braccio,
evidenza, impatto, decisione, modifica applicata, verifica e stato. Nessuna
decisione può dipendere dall'esito atteso delle ipotesi.

## 4. Criteri di uscita dal pilot

Lo studio principale può partire solo quando:

- non restano problemi bloccanti o ad alta severità;
- gli eventi necessari a RQ4 sono presenti e coerenti;
- le istruzioni sono comprensibili nei tre bracci;
- l'export e `backend/analyze_user_study.py` funzionano su dati tecnici marcati;
- tutte le modifiche post-pilot sono documentate;
- applicazione, prompt, dataset, istruzioni e piano di analisi sono congelati.

Una modifica materiale successiva richiede un emendamento esplicito e una nuova
verifica della comparabilità.

## 5. Studio principale

Obiettivo pianificato: almeno 34 casi completi per braccio, reclutando circa 114
persone per compensare esclusioni e abbandoni. Un campione inferiore deve essere
etichettato esplorativo.

Durante la raccolta:

1. non osservare risultati aggregati per decidere quando fermarsi;
2. applicare criteri di esclusione e gestione delle deviazioni già fissati;
3. non sostituire partecipanti o spostare record fra bracci manualmente;
4. registrare indisponibilità tecniche e ripetizioni di sessione;
5. conservare separatamente identificativi operativi e dati analitici;
6. eseguire backup cifrati e controllo periodico degli hash.

## 6. Data lock e analisi

Alla chiusura:

1. esportare partecipanti, outcome e log una sola volta nel pacchetto congelato;
2. calcolare e registrare hash SHA-256;
3. chiudere il registro di deviazioni ed esclusioni prima dell'analisi;
4. eseguire `backend/analyze_user_study.py` come descritto in
   `docs/19-user-study-analysis.md`;
5. verificare Manual vs AI+UI per RQ0 e AI-only vs AI+UI per RQ3;
6. trattare le analisi dei pattern RQ4 come esplorative;
7. riportare numerosità, esclusioni, dati mancanti, effect size e intervalli di
   confidenza anche in presenza di risultati nulli;
8. non reintrodurre NASA-TLX o SUS nel dataset o nel paper corrente.

## 7. Elementi che richiedono persone reali

Restano necessariamente umani: consenso, partecipazione al pilot e allo studio,
debrief facoltativo, valutazione degli outcome che richiede giudizio esperto e
approvazione finale del testo scientifico. Queste attività non possono essere
sostituite da run LLM o record simulati.
