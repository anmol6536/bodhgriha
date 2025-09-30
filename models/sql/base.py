# base.py
from __future__ import annotations

from datetime import datetime
from enum import IntFlag, auto
from typing import Any, Dict, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    BigInteger,
    MetaData,
    String,
    Text,
    func,
    text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Computed

# ---------- Naming convention (stable Alembic diffs)
naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=naming_convention)


# ---------- Mixins
class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# ---------- Role bits (bit flags)
class RoleBits(IntFlag):
    MEMBER = auto()  # 1
    INSTRUCTOR = auto()  # 2
    EDITOR = auto()  # 4
    STAFF = auto()  # 8
    ADMIN = auto()  # 16


# ---------- Models
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(CITEXT, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(200), nullable=False)
    last_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    role_bits: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default=text(str(int(RoleBits.MEMBER))))
    # arbitrary per-user metadata (preferences, profile fields, etc.)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # relationships
    posts: Mapped[list["BlogPost"]] = relationship(back_populates="author", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_active", "is_active"),
    )

    # convenience helpers
    def has_role(self, role: RoleBits) -> bool:
        return bool(RoleBits(self.role_bits) & role)

    def add_role(self, role: RoleBits) -> None:
        self.role_bits = int(RoleBits(self.role_bits) | role)

    def remove_role(self, role: RoleBits) -> None:
        self.role_bits = int(RoleBits(self.role_bits) & ~role)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} roles={RoleBits(self.role_bits)}>"


class BlogPost(TimestampMixin, Base):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    # routing/seo
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)

    # content
    body_md: Mapped[str] = mapped_column(Text, nullable=True)  # source markdown
    body_html: Mapped[str] = mapped_column(Text, nullable=False)  # sanitized render
    body_text: Mapped[str] = mapped_column(Text, nullable=False)  # stripped for search

    # arbitrary metadata from front matter (tags, hero_image, reading_time, etc.)
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # publishing state
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # author
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    author: Mapped[Optional[User]] = relationship(back_populates="posts")

    # Postgres generated column for full-text search
    search_tsv: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(text("to_tsvector('english', body_text)"), persisted=True),  # PG16 supports persisted generated
        nullable=False,
    )

    __table_args__ = (
        # unique lower(slug) (case-insensitive)
        Index("uq_blog_posts_slug_lower", func.lower(slug), unique=True),
        # GIN index for search
        Index("ix_blog_posts_search_tsv", search_tsv, postgresql_using="gin"),
        # quick listings
        Index("ix_blog_posts_published", "is_published", "published_at"),
        CheckConstraint("char_length(slug) >= 3", name="slug_min_len"),
    )

    def __repr__(self) -> str:
        return f"<BlogPost id={self.id} slug={self.slug!r} published={self.is_published}>"


# ---------- Bootstrap helpers (extensions, etc.)
def ensure_postgres_extensions(bind) -> None:
    """
    Create required PG extensions if missing.
    Call once at startup (admin connection).
    """
    from sqlalchemy import text as sql_text
    with bind.begin() as conn:
        conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS citext"))
        # tsvector is built-in; no extension needed for basic English config
        # If you use unaccent or pg_trgm later:
        # conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        # conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))


# ---------- Optional: materialized convenience for search (example)
def search_posts(session, query: str, limit: int = 20) -> list[BlogPost]:
    """Simple full-text search on BlogPost.body_text."""
    from sqlalchemy import select
    ts_query = func.plainto_tsquery("english", query)
    stmt = (
        select(BlogPost)
        .where(BlogPost.search_tsv.op("@@")(ts_query))
        .where(BlogPost.is_published.is_(True))
        .order_by(func.ts_rank_cd(BlogPost.search_tsv, ts_query).desc(), BlogPost.published_at.desc())
        .limit(limit)
    )
    return list(session.scalars(stmt))
