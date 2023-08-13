import sys
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

from pydantic import BaseSettings, PostgresDsn, validator


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        case_sensitive = True

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    SQLALCHEMY_DATABASE_URI: Optional[PostgresDsn] = None

    @validator("SQLALCHEMY_DATABASE_URI", pre=True)
    def assemble_db_connection(cls, v: Optional[str], values: Dict[str, Any]) -> Any:
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme="postgresql",
            user=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_SERVER"),
            path=f"/{values.get('POSTGRES_DB') or ''}",
        )

    PROJECT_NAME: str
    LOGGER_FORMAT: str = "[%(asctime)s][%(name)s][P:%(process)d][T:%(thread)d][%(module)s:%(lineno)d][%(levelname)s] %(message)s"
    DEBUG: bool = False

    SERVER_PORT: int = 5000
    SERVER_HOST: str = "0.0.0.0"
    BASE_HOSTNAME_URL: str = "http://127.0.0.1:5000"
    PRONUNCIATION_DIR: str = "./data/"

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str
    REDIS_DB_QUEUE: int = 1
    REDIS_PRONUNCIATION_QUEUE_KEY: str = "PRONUNCIATION"


@lru_cache
def get_settings():
    settings = Settings()
    return settings


@lru_cache
def get_logger():
    settings = Settings()
    logger = logging.getLogger(settings.PROJECT_NAME)
    if settings.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(settings.LOGGER_FORMAT)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
