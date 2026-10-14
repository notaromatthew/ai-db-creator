from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    llm_provider: str = "vertex"
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
    # Modelli selezionabili dalle impostazioni (separati da virgola). In produzione lasciare fuori i modelli piu' costosi.
    vertex_allowed_models: str = "gemini-2.5-flash-lite,gemini-2.5-flash,gemini-2.5-pro"


    upload_dir: str = str(Path(__file__).parent.parent / "uploads")
    projects_dir: str = str(Path(__file__).parent.parent / "projects")
    log_level: str = "DEBUG"
    experiment_mode: bool = False
    # Modalita' ricerca: strumenti di studio (benchmark, questionari, log delle
    # interazioni, manifest dei run). Spenta = resta solo il prodotto.
    # Si cambia con la variabile RESEARCH_MODE su Coolify e un redeploy.
    research_mode: bool = False
    # Quote giornaliere per utente (valori bassi di proposito, modificabili dall'admin).
    default_daily_ai_quota: int = 20
    max_upload_mb: int = 25
    max_projects_per_user: int = 10
    daily_ai_budget_total: int = 500  # tetto globale di chiamate AI al giorno

    # Database PostgreSQL
    # Nessuna credenziale di default: in produzione DATABASE_URL arriva da Coolify.
    database_url: str = "sqlite:///./app.db"

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
    # Richiede la verifica dell'email (serve SMTP configurato nel realm). Il ruolo admin
    # viene assegnato solo a email verificate, quindi non spegnerla in produzione.
    keycloak_verify_email: bool = True
    # Issuer atteso del token; vuoto = "{keycloak_url}/realms/{keycloak_realm}". Se il backend raggiunge Keycloak
    # con un URL interno diverso da quello pubblico del token, impostalo al valore pubblico.
    keycloak_issuer: str = ""
    # Sale per l'HMAC che lega l'iscrizione allo studio all'account senza salvarne l'id (STUDY_ACCOUNT_SALT).
    study_account_salt: str = ""
    # Il token deve essere stato emesso per questo client (azp) o averlo tra le audience.
    keycloak_check_client: bool = True
    # development | test | production: solo in development/test sono ammessi redirect URI "*".
    environment: str = "production"
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

