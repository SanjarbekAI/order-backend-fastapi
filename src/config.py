from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / .env.

    Every value has a development-friendly default so the app, the test suite
    and Alembic can all import this module without a populated environment.
    Production overrides everything through real environment variables.
    """

    # --- Infrastructure -------------------------------------------------------
    database_url: str = "postgresql://marketplace:marketplace_pass@localhost:5433/marketplace_db"
    redis_url: str = "redis://localhost:6379/0"

    db_pool_min_size: int = 5
    db_pool_max_size: int = 20

    # --- Auth ---------------------------------------------------------------
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # --- Domain knobs -----------------------------------------------------
    order_reservation_minutes: int = 15
    product_cache_ttl_seconds: int = 60

    app_env: str = "development"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
