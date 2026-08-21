import os
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{BASE_DIR / 'email_agent.db'}"


def get_database_url() -> str:
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


DATABASE_URL = get_database_url()

engine_kwargs: dict[str, object] = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql"):
    engine_kwargs["connect_args"] = {"sslmode": "require", "connect_timeout": 10}
    engine_kwargs["pool_recycle"] = 1800

engine = create_engine(DATABASE_URL, pool_pre_ping=True, **engine_kwargs)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_engine() -> Engine:
    return engine


def get_session_factory() -> sessionmaker:
    return SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.database.base import Base
    from app.database.models import ChatSession, Message, OAuthAccount, ScheduledEmail, User

    Base.metadata.create_all(bind=engine)
