# Ollama e GOOGLE_API_KEY: solo sviluppo

- `docker-compose.coolify.yml` (produzione) e `docker-compose.staging.yml` non contengono piu' `OLLAMA_*`, `GOOGLE_API_KEY` ne' chiavi Vertex.
  Il provider predefinito e' `vertex`, che con `LLM_GATEWAY_URL` passa dal gateway Cloud Run.
- Il provider Ollama resta nel codice (`backend/app/core/llm.py`) e in `docker-compose.yml` (sviluppo locale): serve agli sviluppatori senza GPU remota ne' costi.
- Il provider `google` (GOOGLE_API_KEY) resta nel codice per uso locale; non e' configurato in produzione.
- Se un giorno serve Ollama in produzione, va riaggiunto esplicitamente al compose e documentato; oggi senza GPU non serve.
- Su Coolify vanno eliminate a mano (con il via di Davide) le variabili `OLLAMA_*` e `GOOGLE_API_KEY` ancora presenti nelle impostazioni dell'app.
