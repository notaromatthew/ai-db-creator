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




    # SonarQube
    sonarqube_url: str = "http://o4sn9bs961jvxn32hs18a81p.89.168.29.98.sslip.io:9000"

    # Global throttle applied to every LLM API call made by the app. Guards
    # against exceeding provider rate limits (default 15 requests/minute).
    llm_max_requests_per_minute: int = 15
    llm_temperature: float = 0.1
    llm_top_p: float = 0.95
    llm_max_tokens: int = 4096

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

