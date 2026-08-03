# Contributing / Linee Guida di Contributo

## Italiano

### Filosofia

AI-DB-Creator è un progetto di ricerca scientifica applicata. Contribuire significa migliorare non solo il software, ma anche la sua qualità come infrastruttura sperimentale. Ogni contributo dovrebbe rafforzare almeno una di queste dimensioni:

- affidabilità del prodotto
- chiarezza del codice
- riproducibilità degli esperimenti
- qualità della documentazione
- capacità di collaborazione tra agenti e persone

### Prima di iniziare

Leggere almeno:

- `README.md`
- `AGENTS.md`
- `docs/00-project-overview.md`
- `docs/01-multi-agent-playbook.md`
- `docs/09-api-dataflow-map.md`

### Regole pratiche

- evitare modifiche distruttive non richieste
- se si cambia il comportamento, aggiornare anche la documentazione
- se si toccano prompt, popolamento o metriche, esplicitare l'impatto sulla comparabilità dei risultati
- distinguere sempre fix di prodotto da cambiamento metodologico

### Pull request o handoff interni

Ogni contributo dovrebbe chiarire:

- problema affrontato
- soluzione adottata
- file toccati
- rischi residui
- verifiche eseguite

### Qualità garantita

Prima di inviare un contributo, assicurarsi che:

- la suite backend sia verde: `python -m pytest` (Python 3.13, vedere `backend/.python-version`)
- la build frontend compili: `npm run build`
- i test frontend passino: `npm run test`

### Standard per documentazione

La documentazione strategica del progetto è bilingue. Quando si aggiungono documenti strategici o manuali, mantenere:

- sezione in italiano
- sezione in inglese
- tono tecnico, formale e adatto a uso accademico

---

## English

### Philosophy

AI-DB-Creator is a scientific applied-research project. Contributing means improving not only the software but also its quality as experimental infrastructure. Every contribution should strengthen at least one of the following:

- product reliability
- code clarity
- experimental reproducibility
- documentation quality
- collaboration between agents and people

### Before starting

Read at least:

- `README.md`
- `AGENTS.md`
- `docs/00-project-overview.md`
- `docs/01-multi-agent-playbook.md`
- `docs/09-api-dataflow-map.md`

### Practical rules

- avoid destructive changes unless explicitly requested
- if behavior changes, update documentation as well
- if prompts, population, or metrics change, state the impact on result comparability
- always distinguish product fixes from methodological changes

### Pull requests or internal reviews

Each contribution should clarify:

- problem addressed
- solution adopted
- files touched
- residual risks
- verification performed

### Test quality

Before submitting a contribution, make sure that:

- the backend suite passes: `python3 -m pytest` (Python 3.13, see `backend/.python-version`)
- the frontend builds: `npm run build`
- the frontend tests pass: `npm run test`

### Documentation standard

The strategic documentation is bilingual. When adding strategic documents or manuals, keep:

- an Italian section
- an English section
- a technical, academically suitable tone