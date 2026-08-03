from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    llm_provider: str = "openai"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    groq_api_key: str = ""
    groq_model: str = "llama3-70b-8192"

    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"

    google_api_key: str = ""
    google_model: str = "gemini-2.0-flash"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    use_ollama: bool = False

    upload_dir: str = str(Path(__file__).parent.parent / "uploads")
    projects_dir: str = str(Path(__file__).parent.parent / "projects")
    log_level: str = "DEBUG"
    experiment_mode: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
