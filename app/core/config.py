from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ShopEase User Service"
    app_version: str = "1.0.0"
    app_port: int = 8004
    debug: bool = False

    db_host: str = "127.0.0.1"
    db_port: int = 3309
    db_name: str = "shopease_user_db"
    db_user: str = "shopease_user"
    db_password: str = ""
    db_root_password: str = ""

    # These values MUST match the existing ShopEase Authentication Service.
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "shopease-auth-service"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return (
            f"mysql+pymysql://{user}:{password}@{self.db_host}:{self.db_port}/"
            f"{self.db_name}?charset=utf8mb4"
        )


@lru_cache

def get_settings() -> Settings:
    return Settings()
