from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "dev-secret-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ECOM_OPPO_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = "development"
    sqlite_dev_db_path: str = "./data/ecom_oppo.db"
    database_url: str = ""
    jwt_secret_key: str = DEFAULT_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    bcrypt_rounds: int = 12
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )
    llm_api_key: str = Field(default="", validation_alias="LLM_API_KEY")
    llm_base_url: str = Field(default="", validation_alias="LLM_BASE_URL")
    llm_model: str = Field(
        default="llama-3.3-70b-versatile",
        validation_alias="LLM_MODEL",
    )
    llm_timeout_seconds: int = Field(
        default=15,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key.strip() and self.llm_base_url.strip())

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if self.app_env.lower() == "test":
            return "sqlite+aiosqlite:///:memory:"
        return f"sqlite+aiosqlite:///{Path(self.sqlite_dev_db_path).as_posix()}"

    @classmethod
    def for_test(
        cls, *, database_url: str = "sqlite+aiosqlite:///:memory:"
    ) -> "Settings":
        return cls(
            app_env="test",
            sqlite_dev_db_path="./data/ecom_oppo-test.db",
            database_url=database_url,
        )

    @model_validator(mode="after")
    def validate_secret_for_environment(self) -> "Settings":
        non_dev_env = self.app_env.lower() not in {"dev", "development", "local", "test"}
        if non_dev_env and self.jwt_secret_key == DEFAULT_JWT_SECRET:
            raise ValueError("ECOM_OPPO_JWT_SECRET_KEY must be set outside development")
        return self


settings = Settings()
