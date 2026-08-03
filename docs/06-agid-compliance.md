# Conformità AGID — Note di allineamento

## 1. Premessa

Questo documento non costituisce parere legale. Serve a mappare AI-DB-Creator rispetto ad alcune aspettative tipiche di interoperabilità, accessibilità, sicurezza, tracciabilità e governance che diventano rilevanti quando una piattaforma software si avvicina a contesti pubblici o sanitari.

## 2. Stato attuale

AI-DB-Creator non può essere considerato conforme AGID nello stato attuale. Può però essere considerato un buon punto di partenza tecnico, a condizione di distinguere con chiarezza tra:

- stato presente della piattaforma
- direzione di evoluzione verso allineamento normativo e organizzativo

## 3. Aree rilevanti

### 3.1 Accessibilità

La UI è moderna e strutturata, ma non risultano evidenze di audit sistematico rispetto ai requisiti di accessibilità. Per un allineamento serio servirebbero:

- verifica semantica dei componenti
- navigazione completa da tastiera
- controllo contrasto e leggibilità
- audit con screen reader

### 3.2 Sicurezza applicativa

Esistono basi corrette (configurazione tramite variabili d'ambiente, rate limiting), ma mancano elementi essenziali:

- autenticazione utenti
- autorizzazione per ruoli
- restrizione CORS in produzione
- segregazione dei dati per identità o dominio d'uso

### 3.3 Protezione dei dati

Il progetto gestisce dati di ricerca (modelli di dominio da detti non esperti) e quindi deve essere progettato come sistema con attenzione alla sensibilità informativa, anche se usato in ricerca. Serve definire (già avviato in `docs/13-data-governance.md`):

- finalità del trattamento
- basi giuridiche se applicabile
- tempi di conservazione
- procedure di cancellazione
- misure di cifratura e protezione del trasporto

### 3.4 Tracciabilità e audit

I log applicativi e la persistenza dei run sono un buon inizio, ma non bastano. Sarebbe necessario poter ricostruire:

- chi ha avviato una generazione/popolazione
- con quale configurazione e quale modello
- su quali documenti
- con quale esito

### 3.5 Interoperabilità e portabilità

Area di partenza più forte rispetto ai tipici prototipi:

- uso di Docker Compose
- configurazione tramite variabili ambiente
- servizi separati e API endpoint chiari (vedi `docs/09-api-dataflow-map.md`)
- export multi-dialetto (DDL + INSERT)

Questi elementi riducono il lock-in tecnico e semplificano la documentazione di esercizio.

## 4. Piano minimo di avvicinamento

1. introdurre autenticazione e profili
2. documentare policy di dati e retention
3. aggiungere audit trail degli eventi sensibili
4. eseguire una valutazione accessibilità
5. restringere CORS e formalizzare il deploy sicuro

## 5. Confronto con l'intervento umano

La compliance organizzativa e il carico amministrativo dell'uso in contesti pubblici/sanitari sono ancora di dominio ipotetico. Le valutazioni comparative rispetto al processo manuale — dove un utente senza competenze tecniche dovrebbe rispettare vincoli simili — restano da definire **[non ancora]**: nessun paragone determinato con l'intervento umano raccolto.