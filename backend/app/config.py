from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    llm_provider: str = "ollama"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"

    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    # Vertex AI (Google Cloud). Pensato per il costo minimo: modello "lite",
    # tetto ai token di output e regione UE. Le credenziali arrivano da un
    # service account (JSON in variabile d'ambiente) oppure da ADC/Workload
    # Identity quando l'app gira su Google Cloud.
    vertex_project: str = ""
    vertex_location: str = "europe-west4"
    vertex_model: str = "gemini-2.5-flash-lite"
    vertex_credentials_json: str = ""
    vertex_max_output_tokens: int = 2048

    ollama_mode: str = "remote"  # "remote" vs "local"
    ollama_base_url: str = "https://ollamaapi-u11fj34m2h9druz26hamz3xb.89.168.29.98.sslip.io"
    ollama_api_key: str = ""
    ollama_model: str = "gemma2:9b"
    use_ollama: bool = True

    upload_dir: str = str(Path(__file__).parent.parent / "uploads")
    projects_dir: str = str(Path(__file__).parent.parent / "projects")
    log_level: str = "DEBUG"
    experiment_mode: bool = False

    # Database PostgreSQL
    database_url: str = "postgresql://postgres:postgres@89.168.29.98:12000/postgres"

    # Keycloak OIDC Auth & Realm Admin
    keycloak_url: str = "https://keycloak-pw9ut4s1h3aodstrsw1gd84o.89.168.29.98.sslip.io"
    keycloak_realm: str = "aidbcreator"
    keycloak_client_id: str = "aidbcreator-app"
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = ""
    enable_auth: bool = True
    admin_role: str = "aidb-admin"
    # URL pubblico dell'app (es. https://app.tecniaweb.it): usato per limitare
    # redirect URI e web origins del client Keycloak. Vuoto = nessuna restrizione.
    app_public_url: str = ""
    keycloak_allow_registration: bool = True
    keycloak_login_theme: str = ""

    host: str = "0.0.0.0"
    port: int = 8000
    cors_allow_origin_regex: str = r"https?://.*"




    # SonarQube
    sonarqube_url: str = "http://o4sn9bs961jvxn32hs18a81p.89.168.29.98.sslip.io:9000"

    # Global throttle applied to every LLM API call made by the app. Guards
    # against exceeding provider rate limits (default 15 requests/minute).
    llm_max_requests_per_minute: int = 15
    llm_temperature: float = 0.1
    llm_top_p: float = 0.95
    llm_max_tokens: int = 4096
    # Cache opzionale delle risposte deterministiche (temperatura 0). Spenta
    # di default: negli esperimenti ogni run deve campionare davvero il modello.
    llm_cache_enabled: bool = False
    llm_cache_max_entries: int = 256

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

