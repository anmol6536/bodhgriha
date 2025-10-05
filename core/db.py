# core/db.py
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from models import Base
from models.sql import ensure_postgres_extensions
from utilities.connection import EngineManager

ENGINE = EngineManager.get('BODHGRIHA')
SessionLocal = sessionmaker(bind=ENGINE, expire_on_commit=False, autoflush=False)


def get_session():
    return SessionLocal()


@contextmanager
def uow(readonly: bool = False):
    db = SessionLocal()
    try:
        if readonly:
            trans = db.begin()
            try:
                db.execute(text("SET TRANSACTION READ ONLY"))
                yield db
                trans.commit()  # ✅ commit, not rollback
            except:
                trans.rollback()
                raise
        else:
            with db.begin():
                yield db
    except:
        if db.in_transaction():
            db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Dev/test convenience: create extensions and tables.
    Do NOT call in production. Use Alembic instead.
    """
    # create schemas
    from sqlalchemy import text

    with ENGINE.connect() as conn:
        SCHEMAS = [
            'core',
            'courses',
            'registrations',
            'payments',
            'admin',
            'auth',
            'audit',
            'notifications',
            'reports',
            'analytics',
            'content',
        ]
        for schema in SCHEMAS:
            conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))

        conn.commit()

    ensure_postgres_extensions(ENGINE)
    Base.metadata.create_all(ENGINE)
