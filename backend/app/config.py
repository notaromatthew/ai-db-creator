from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    llm_provider: str = "ollama"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"

    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    ollama_mode: str = "local"  # "remote" vs "local"
    ollama_base_url: str = "http://localhost:11434"
    ollama_api_key: str = ""
    ollama_model: str = "gemma2:9b"
    use_ollama: bool = False

    upload_dir: str = str(Path(__file__).parent.parent / "uploads")
    projects_dir: str = str(Path(__file__).parent.parent / "projects")
    log_level: str = "DEBUG"
    experiment_mode: bool = False
    experiment_assignment_seed: str = "draft-seed"
    experiment_pseudonym_secret: str = "development-only-change-me"
    rq4_hash_salt: str = "development-only-change-me"
    bootstrap_keycloak: bool = False

    # Database PostgreSQL
    database_url: str = "sqlite:///./app.db"

    # Keycloak OIDC Auth & Realm Admin
    keycloak_url: str = "http://localhost:8080"
    keycloak_realm: str = "aidbcreator"
    keycloak_client_id: str = "aidbcreator-app"
    keycloak_admin_user: str = "admin"
    keycloak_admin_password: str = ""
    enable_auth: bool = True
    cors_allowed_origins: str = "http://localhost:3000,http://127.0.0.1:3000"




    # SonarQube
    sonarqube_url: str = "http://localhost:9000"

    # Global throttle applied to every LLM API call made by the app. Guards
    # against exceeding provider rate limits (default 8 requests/minute).
    llm_max_requests_per_minute: int = 8
    llm_temperature: float = 0.1
    llm_top_p: float = 0.95
    llm_max_tokens: int = 4096

    @model_validator(mode="after")
    def validate_experiment_secrets(self):
        placeholders = {"", "draft-seed", "development-only-change-me", "replace-before-pilot"}
        if self.experiment_mode and any(value in placeholders for value in (
            self.experiment_assignment_seed, self.experiment_pseudonym_secret, self.rq4_hash_salt
        )):
            raise ValueError("EXPERIMENT_MODE requires non-placeholder assignment, pseudonym and RQ4 secrets")
        return self

settings = Settings()

