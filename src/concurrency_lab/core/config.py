from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    mysql_host: str = "127.0.0.1"
    mysql_port: int = Field(default=3306, ge=1, le=65535)
    mysql_database: str = "concurrency_lab"
    mysql_user: str = "lab"
    mysql_password: SecretStr = Field(min_length=1)
    redis_host: str = "127.0.0.1"
    redis_port: int = Field(default=6379, ge=1, le=65535)
    redis_password: SecretStr = Field(min_length=1)
    db_pool_size: int = Field(default=5, ge=1)
    db_max_overflow: int = Field(default=5, ge=0)
    db_pool_timeout: float = Field(default=1, gt=0)
    db_pool_recycle: int = Field(default=1800, ge=1)
    redis_max_connections: int = Field(default=10, ge=1)
    io_timeout: float = Field(default=1, gt=0)
    readiness_timeout: float = Field(default=2, gt=0)
    business_enabled: bool = False
    business_database: Literal["concurrency_lab_business", "concurrency_lab_business_test"] = (
        "concurrency_lab_business"
    )
    business_request_timeout: float = Field(default=5, gt=0, le=60)

    @property
    def database_url(self) -> URL:
        return URL.create(
            "mysql+asyncmy",
            username=self.mysql_user,
            password=self.mysql_password.get_secret_value(),
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )
