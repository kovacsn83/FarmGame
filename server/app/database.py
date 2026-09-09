from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_database_url


class Base(DeclarativeBase):
    pass


def create_database_engine(database_url=None):
    url = database_url or get_database_url()
    options = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **options)


def create_session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
