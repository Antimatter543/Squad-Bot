import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


enabled = os.getenv("DB_ENABLED", True)


class DBConfig:
    enabled = os.getenv("DB_ENABLED", True)
    name = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5432")

    def __init__(self) -> None:
        self._dbhost = f"{self.host}:{self.port}"
        self.uri = f"postgresql+asyncpg://{self.user}:{self.password}@{self._dbhost}/{self.name}"


dbconfig = DBConfig()

engine = create_async_engine(dbconfig.uri) if enabled else None
Session = sessionmaker(engine, class_=AsyncSession) if enabled else None
