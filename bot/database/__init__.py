import os

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class DBConfig:
    enabled = os.getenv("DB_ENABLED", True)
    name = os.getenv("DB_NAME", "discord")
    user = os.getenv("DB_USER", "discord")
    password = os.getenv("DB_PASSWORD", "discord")
    host = os.getenv("DB_HOST", "127.0.0.1")
    port = os.getenv("DB_PORT", "5432")
    dockerservice = os.getenv("DB_DOCKER_SERVICE_NAME", None)


dbconfig = DBConfig()

_dbhost = f"{dbconfig.host}:{dbconfig.port}" if dbconfig.dockerservice is None else dbconfig.dockerservice

engine = create_async_engine(f"postgresql+asyncpg://{dbconfig.user}:{dbconfig.password}@{_dbhost}/{dbconfig.name}")
Session = sessionmaker(engine, class_=AsyncSession)
