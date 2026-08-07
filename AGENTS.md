# AGENTS / Guida per Agenti

## Italiano

### Scopo

Questo file è il punto di ingresso operativo per agenti AI e collaboratori tecnici che lavorano su AI-DB-Creator. Serve a ridurre il costo di onboarding e ad allineare rapidamente il lavoro al carattere scientifico del progetto.

### Identità del progetto

AI-DB-Creator è una piattaforma di ricerca in AI applicata alla generazione di database, non un semplice generatore di SQL. Le aree più sensibili sono:

- generazione e normalizzazione di schemi relazionali
- popolamento full-LLM con fallback deterministico e provenance
- riproducibilità sperimentale (manifesti, hash, log)
- confronto tra condizioni sperimentali
- documentazione e governance

### Regole di lavoro

- leggere i documenti strategici prima di fare cambiamenti sostanziali
- evitare di trattare le inferenze come fatti: separare osservazioni, ipotesi e proposte
- non cambiare in modo silenzioso prompt, metriche o semantica degli esperimenti
- se un cambiamento modifica la comparabilità sperimentale, documentarlo esplicitamente

### Ordine di lettura consigliato

1. `README.md`
2. [docs/wiki/INDEX.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/INDEX.md) (Wiki Scientifico ed Operativo)
3. [docs/wiki/02-ai-agent-protocol-and-comments.md](file:///Users/davide/Documents/repos/ai-db-creator/docs/wiki/02-ai-agent-protocol-and-comments.md) (Protocollo & Registro Commenti / RFC Agenti AI)
4. `docs/00-project-overview.md`
5. `docs/01-multi-agent-playbook.md`
6. `docs/02-technical-manual.md`
7. `docs/09-api-dataflow-map.md`


### Aree della repo

- `backend/`: logica di dominio, API, servizi, modelli, parser, generazione database
- `frontend/`: UI e workflow operativi
- `docs/`: base di conoscenza del progetto
- `paper/`: articolo scientifico e riferimenti

### Linee guida per la scrittura del codice (AI)

Seguire sempre i pattern esistenti nei moduli contigui, non introdurre dipendenze senza verificarle in `requirements.txt`/`package.json`, e mantenere la suite di test verde (backend `pytest`, frontend `vitest`). Non aggiungere commenti se non richiesti.

### Cosa documentare sempre

- nuove API
- cambiamenti a modelli persistenti
- modifiche a prompt o pipeline di popolamento
- assunzioni operative per deploy e ambienti

---

## English

### Purpose

This file is the operational entry point for AI agents and technical collaborators working on AI-DB-Creator. Its goal is to reduce onboarding cost and quickly align work with the scientific nature of the project.

### Project identity

AI-DB-Creator is an AI research platform for database generation, not a generic SQL assistant. The most sensitive areas are:

- generation of normalized relational schemas
- full-LLM population with deterministic fallback and provenance
- experimental reproducibility (manifests, hashes, logs)
- comparison across experimental conditions
- documentation and governance

### Working rules

- read the strategic documents before making substantial changes
- do not treat inference as fact: separate observation, hypothesis, proposal
- do not silently change prompts, metrics, or population semantics
- if a change affects experimental comparability, document it explicitly

### Required reading order

1. `README.md`
2. `docs/00-project-overview.md`
3. `docs/01-multi-agent-playbook.md`
4. `docs/02-technical-manual.md`
5. `docs/09-api-dataflow-map.md`

### Repository areas

- `backend/`: domain logic, APIs, services, models, pipelines, DB generation
- `frontend/`: UI and operational workflows
- `docs/`: project knowledge base
- `paper/`: LaTeX paper and references

### AI Coding Guidelines

Follow existing patterns in adjacent modules, never introduce dependencies without checking `requirements.txt`/`package.json`, and keep the test suite green (backend `pytest`, frontend `vitest`/`build`). Do not add comments unless required.

### Always document

- new APIs
- changes to persistent models
- prompt or population-query changes
- operational assumptions for deployment and environments