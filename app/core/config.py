from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str
    debug: bool = False
    api_key_prefix: str = "sk-relay-"

    price_cache_ttl: int = 300
    price_fetch_interval: int = 300
    health_check_interval: int = 30
    failure_threshold: int = 3
    recovery_threshold: int = 2
    max_retries: int = 3


settings = Settings()
