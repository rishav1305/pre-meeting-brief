from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    phase: int = 1

    # Vercel Postgres auto-binds these
    postgres_url: str = ""
    postgres_url_non_pooling: str = ""

    # Optional for Phase 2+
    anthropic_api_key: str = ""
    anthropic_base_url: str = ""
    admin_password: str = ""


settings = Settings()
