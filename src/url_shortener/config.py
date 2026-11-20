from pydantic import Field, NonNegativeInt, PositiveInt, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: PostgresDsn
    database_connect_timeout_seconds: PositiveInt = 5
    database_pool_size: PositiveInt = 5
    database_max_overflow: NonNegativeInt = 10

    redis_url: RedisDsn
    redis_key_prefix: str = Field(default="url-shortener", pattern=r"^[^\s]+$")
    redis_connect_timeout_seconds: float = Field(default=0.2, gt=0, allow_inf_nan=False)
    redis_cache_timeout_seconds: float = Field(default=0.2, gt=0, allow_inf_nan=False)
    redis_publish_timeout_seconds: float = Field(default=0.2, gt=0, allow_inf_nan=False)
    redis_worker_timeout_seconds: float = Field(default=5, gt=1, allow_inf_nan=False)
    cache_ttl_seconds: PositiveInt = 3600

    max_code_attempts: PositiveInt = 5

    metrics_host: str = "127.0.0.1"
    metrics_port: int | None = Field(default=None, ge=1, le=65535)
