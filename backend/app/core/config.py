from pydantic import PostgresDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Use top level .env file (one level above ./backend/)
        env_file="../.env",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "RPG AI Game"
    PROJECT_VERSION: str = "0.0.1"

    OLLAMA_SERVER: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "gpt-oss:20b"

    POSTGRES_SERVER: str = "db"  # docker compose service name
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "gameuser"
    POSTGRES_PASSWORD: str = "gamepass"
    POSTGRES_DB: str = "gamedb"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return PostgresDsn.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )


settings = Settings()
print(f">>> Using database at {str(settings.SQLALCHEMY_DATABASE_URI)}")
