"""Configuration management for Mnemonic backend."""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mnemonic.exceptions import LLMConfigError


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str = "postgresql://mnemonic:changeme@localhost:5432/mnemonic"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Environment
    environment: str = "development"
    debug: bool = True
    log_level: str = "DEBUG"

    # LLM
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4"

    # Server
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Authentication
    secret_key: str = "development-secret-key-change-in-production"
    jwt_expiration_minutes: int = 60 * 24 * 7  # 7 days
    password_hash_rounds: int = 12

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @field_validator("openrouter_api_key")
    @classmethod
    def validate_llm_config_production(cls, v: str, info) -> str:
        """Validate LLM configuration in production.

        In production mode, the OpenRouter API key must be provided, as LLM
        variations are a core feature of the spaced repetition system.

        Args:
            v: The API key value
            info: Validation context containing other field values

        Returns:
            The validated API key

        Raises:
            LLMConfigError: If in production mode without a valid API key
        """
        # Access the environment field from the context
        data = info.data
        environment = data.get("environment", "development")

        if environment == "production" and not v:
            raise LLMConfigError(
                "OpenRouter API key is required in production. "
                "Please set OPENROUTER_API_KEY environment variable. "
                "Get your key at https://openrouter.ai/keys"
            )
        return v


settings = Settings()
