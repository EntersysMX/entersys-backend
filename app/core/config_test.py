# app/core/config_test.py - Temporary config for local testing with SQLite
from pydantic_settings import BaseSettings, SettingsConfigDict

class TestSettings(BaseSettings):
    """
    Test configuration using SQLite for local testing
    """
    model_config = SettingsConfigDict(
        env_file=".env", env_ignore_case=True, extra="ignore"
    )

    # --- JWT Settings ---
    SECRET_KEY: str = "dev-secret-key-for-testing-only-2025"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # --- Google OAuth Settings ---
    GOOGLE_CLIENT_ID: str = "96894495492-npdg8c8eeh6oqpgkug2vaalle8krm0so.apps.googleusercontent.com"
    GOOGLE_CLIENT_SECRET: str = "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"

    @property
    def DATABASE_URI(self) -> str:
        """
        SQLite database for testing
        """
        return "sqlite:///./test.db"

# Test settings instance
test_settings = TestSettings()