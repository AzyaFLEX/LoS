from functools import lru_cache
from os import getenv
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, BaseSettings, PostgresDsn, validator


class Settings(BaseSettings):
    load_dotenv()

    PROJECT_NAME: str = Field(default='')
    VERSION: str = Field(default='')
    DEBUG: bool = Field(default=True)

    SECRET: str = Field(default='')

    SERVER_HOST: str = Field(default='localhost')
    SERVER_PORT: int = Field(default=443)

    POSTGRES_DB: str = Field(default='')
    POSTGRES_USER: str = Field(default='')
    POSTGRES_PASSWORD: str = Field(default='')
    POSTGRES_HOST: str = Field(default='')
    POSTGRES_PORT: str = Field(default='')

    SSL_DATA: dict = Field(default={
        'ssl_keyfile': getenv('SSL_KEYFILE'),
        'ssl_certfile': getenv('SSL_CERTFILE')
    })

    SQLALCHEMY_URL: Optional[PostgresDsn] = None

    @validator('SQLALCHEMY_URL', pre=True)
    def get_sqlalchemy_url(cls, v, values):
        if isinstance(v, str):
            return v
        return PostgresDsn.build(
            scheme='postgresql+asyncpg',
            user=values.get('POSTGRES_USER'),
            password=values.get('POSTGRES_PASSWORD'),
            host=values.get('POSTGRES_HOST'),
            port=values.get('POSTGRES_PORT'),
            path=f'/{values.get("POSTGRES_DB")}'
        )

    @validator('SERVER_HOST', pre=True)
    def check_debug_mode(cls, v, values):
        if values.get('DEBUG'):
            return 'localhost'
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
