from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: str

    # Support either a single DB or multiple ERP DB names
    DB_NAME: Optional[str] = None
    DB_NAME_USER: Optional[str] = None
    DB_NAME_FINANCE: Optional[str] = None
    DB_NAME_PURCHASE: Optional[str] = None
    DB_NAME_MASTER: Optional[str] = None
    DB_NAME_USER_NEW: Optional[str] = None

    # Optional settings with sensible defaults
    SECRET_KEY: str = "super-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:3b"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_MODE: str = "local"

    ENCRYPTION_KEY: str = "your-generated-key"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @property
    def database_name(self) -> str:
        return (
            self.DB_NAME
            or self.DB_NAME_USER
            or self.DB_NAME_FINANCE
            or self.DB_NAME_PURCHASE
            or self.DB_NAME_MASTER
            or self.DB_NAME_USER_NEW
            or ""
        )

    @property
    def database_url(self) -> str:
        import urllib.parse

        db_name = self.database_name
        if not db_name:
            raise ValueError("No database name configured (DB_NAME or DB_NAME_USER etc.)")

        escaped_password = urllib.parse.quote_plus(self.DB_PASSWORD)
        return f"mysql+aiomysql://{self.DB_USER}:{escaped_password}@{self.DB_HOST}:{self.DB_PORT}/{db_name}"


settings = Settings()
