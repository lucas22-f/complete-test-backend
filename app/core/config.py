from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Support Backend"

    database_url: str = "sqlite:///./ai_support.db"

    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Optional until chat is called; avoid accidental credential reprs.
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-5-nano"
    chat_timeout_seconds: float = Field(default=60, gt=0, le=300)
    chat_max_output_tokens: int = Field(default=2048, ge=1, le=8192)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
