from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://aaso:aaso_secret@localhost:5432/aaso"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "aaso_memory"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    opencode_api_key: str = "sk-mKYsQXr6bwBlGJ8KIgeaeXCcc7QqnUimNARIEu0TMzUxgtICwMs40CVuJat7y7og"
    opencode_base_url: str = "https://opencode.ai/zen/v1"
    opencode_model: str = "big-pickle"
    llm_provider: str = "stub"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"


settings = Settings()
