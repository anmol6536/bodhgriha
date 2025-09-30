# core/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models.sql.base import Base, ensure_postgres_extensions
from utilities.connection import EngineManager
from contextlib import contextmanager


ENGINE = EngineManager.get('BODHGRIHA')
SessionLocal = sessionmaker(bind=ENGINE, expire_on_commit=False, autoflush=False)


def get_session():
    return SessionLocal()


@contextmanager
def uow(readonly: bool = False):
    db = SessionLocal()
    try:
        if readonly:
            yield db
            db.rollback()  # discard any accidental writes
        else:
            with db.begin():  # begin/commit/rollback handled here
                yield db
    except:
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Dev/test convenience: create extensions and tables.
    Do NOT call in production. Use Alembic instead.
    """
    ensure_postgres_extensions(ENGINE)
    Base.metadata.create_all(ENGINE)
