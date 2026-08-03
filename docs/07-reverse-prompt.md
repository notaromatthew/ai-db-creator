# Prompt Inverso di Rigenerazione

## 1. Scopo

Questo prompt serve a rigenerare il progetto mantenendone l'intento, la forma architetturale e la natura di piattaforma di ricerca. Non deve produrre una semplice "app simile", ma un sistema che conservi i principi strutturali di AI-DB-Creator.

## 2. Prompt inverso

Progetta e implementa una piattaforma full-stack chiamata AI-DB-Creator, orientata alla ricerca scientifica sulla generazione di database relazionali da parte di utenti non esperti. Il sistema deve consentire agli utenti di creare schemi normalizzati e popolare i dati a partire da descrizioni in linguaggio naturale e documenti eterogenei (PDF, Excel, CSV, TXT), e di esplorare il risultato tramite un'interfaccia visuale interattiva.

Requisiti architetturali:

- frontend in React 18 + TypeScript con Vite 5 e TailwindCSS
- backend in FastAPI con SQLAlchemy e Pydantic
- persistenza SQLite per stato dell'applicazione e database generati
- integrazione LLM provider-agnostic (OpenAI, Google Gemini, Groq, OpenRouter, Ollama)
- configurazione interamente guidata da variabili d'ambiente
- orchestrazione locale tramite Docker Compose

Requisiti funzionali:

- generazione di schema relazionale normalizzato (3NF) da prompt o documenti
- popolamento automatico full-LLM con fallback deterministico e provenance tracciabile
- interfaccia CRUD visuale sui dati (modifica celle, aggiunta/eliminazione righe, filtri per colonna)
- query in linguaggio naturale tradotta in SQL
- export multi-dialetto (SQLite, PostgreSQL, MySQL, SQL Server)
- backup e ripristino
- metriche di qualità dello schema e dei dati
- integrazione survey NASA-TLX e SUS

Vincoli di design:

- il sistema deve essere pensato come piattaforma di ricerca, non come prodotto consumer
- il codice deve essere leggibile, modulare e facilmente documentabile
- il dominio sperimentale deve essere persistente e auditabile
- generazione/popolazione deve distinguere chiaramente dati sorgente, configurazione, output e valutazione
- la UI deve risultare moderna e credibile in ambito accademico

Requisiti metodologici:

- preservare la riproducibilità degli esperimenti (manifesti, hash, provenance)
- rendere espliciti prompt e system prompt
- supportare confronti tra condizioni sperimentali (manuale, ai-only, ai+interfaccia)
- consentire futura estensione multi-agente

## 3. Criteri minimi di accettazione

- l'utente può creare uno schema relazionale da una descrizione o da documenti
- l'utente può popolare le tabelle dai documenti caricati
- l'utente può visualizzare e correggere i dati via CRUD
- l'utente può eseguire query in linguaggio naturale
- l'utente può esportare il database in più dialetti SQL
- il sistema può essere avviato e configurato localmente

## 4. Confronto con l'intervento umano

La rigenerazione del prompt inverso non altera il paragone sperimentale che resta pendente. Le valutazioni comparative tra il flusso "con interfaccia" generato qui e l'intervento umano in condizione manual restano da compilare **[non ancora]**.