"""Typed, redacted runtime configuration."""
from __future__ import annotations

from functools import lru_cache
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    environment: str = Field("local", alias="AEGIS_ENVIRONMENT")
    mongodb_uri: SecretStr = Field(SecretStr("mongodb://localhost:27017"), alias="MONGODB_URI")
    mongo_database: str = Field("mydatabase", alias="MONGO_DATABASE")
    orchestrator_token: SecretStr = Field(SecretStr(""), alias="AEGIS_ORCHESTRATOR_TOKEN")
    operator_token: SecretStr = Field(SecretStr(""), alias="AEGIS_OPERATOR_TOKEN")
    normal_workload_enabled: bool = Field(True, alias="AEGIS_NORMAL_WORKLOAD_ENABLED")
    demo_workload_enabled: bool = Field(False, alias="AEGIS_DEMO_WORKLOAD_ENABLED")
    search_recovery_ms: int = Field(2000, ge=1, alias="AEGIS_SEARCH_RECOVERY_MS")
    worker_min_capacity: int = Field(1, ge=1, alias="AEGIS_WORKER_MIN_CAPACITY")
    worker_max_capacity: int = Field(4, ge=1, alias="AEGIS_WORKER_MAX_CAPACITY")

    def safe_summary(self) -> dict[str, object]:
        return {
            "environment": self.environment,
            "mongo_database": self.mongo_database,
            "normal_workload_enabled": self.normal_workload_enabled,
            "demo_workload_enabled": self.demo_workload_enabled,
        }

    def validate_control_plane(self) -> None:
        missing = []
        if not self.orchestrator_token.get_secret_value(): missing.append("AEGIS_ORCHESTRATOR_TOKEN")
        if not self.operator_token.get_secret_value(): missing.append("AEGIS_OPERATOR_TOKEN")
        if missing: raise ValueError(f"required control-plane configuration is missing: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
