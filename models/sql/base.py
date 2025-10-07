# base.py
from __future__ import annotations

from datetime import datetime, timedelta
from enum import IntFlag, auto
from typing import Any, Dict, Optional
import uuid
from enum import Enum

from sqlalchemy import (
    BigInteger, String, Boolean, DateTime, ForeignKey,
    Index, UniqueConstraint, text, func, Enum as SQLEnum
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB, INET, UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from flask_login import UserMixin

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

from models import Base


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
class User(UserMixin, TimestampMixin, Base):
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
        dict(
            schema="auth",
            comment="User accounts with roles, 2FA, sessions, tokens, and related info",
        )
    )

    # convenience helpers
    def has_role(self, role: RoleBits) -> bool:
        return bool(RoleBits(self.role_bits) & role)

    def add_role(self, role: RoleBits) -> None:
        self.role_bits = int(RoleBits(self.role_bits) | role)

    def remove_role(self, role: RoleBits) -> None:
        self.role_bits = int(RoleBits(self.role_bits) & ~role)

    def has_previlige(self, required_role: RoleBits | int) -> bool:
        """
        escalation policy is ordered. E.g., ADMIN > STAFF > EDITOR > INSTRUCTOR > MEMBER
        If allowed for INSTRUCTOR, also allowed for EDITOR, STAFF, ADMIN
        """
        return self.role_bits >= (required_role.value if isinstance(required_role, RoleBits) else required_role)

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} roles={RoleBits(self.role_bits)}>"


# ---- Keep your Base, TimestampMixin, RoleBits, User as-is above this line ----
# (No edits to User)

# ---------- Enums
class TwoFAMethod(str, Enum):
    TOTP = "TOTP"
    SMS = "SMS"  # optional; leave columns nullable if unused
    EMAIL = "EMAIL"  # optional (fallback)
    # Add WEBAUTHN later without breaking existing data


class TokenPurpose(str, Enum):
    EMAIL_VERIFY = "EMAIL_VERIFY"
    PASSWORD_RESET = "PASSWORD_RESET"


# ---------- Address
class Address(TimestampMixin, Base):
    __tablename__ = "addresses"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )

    # Minimal, normalized enough for India-first; extensible globally
    line1: Mapped[str] = mapped_column(String(255), nullable=False)
    line2: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str | None] = mapped_column(String(120))  # e.g., MH, KA
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False)
    country_iso2: Mapped[str] = mapped_column(String(2), nullable=False, server_default=text("'IN'"))

    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    user: Mapped["User"] = relationship(backref="addresses")

    __table_args__ = (
        # At most one primary address per user (enforced by partial unique index)
        Index(
            "ux_addresses_user_primary",
            "user_id",
            unique=True,
            postgresql_where=text("is_primary = true")
        ),
        Index("ix_addresses_user", "user_id"),
        Index("ix_addresses_postal", "postal_code"),
        dict(
            schema="auth",
            comment="User addresses; multiple per user, one primary",
        )
    )


# ---------- Two-Factor Auth (supports TOTP now; SMS/Email optional)
class TwoFactorCredential(TimestampMixin, Base):
    __tablename__ = "two_factor_credentials"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )
    method: Mapped[TwoFAMethod] = mapped_column(SQLEnum(TwoFAMethod, name="twofa_method"), nullable=False)

    # TOTP
    totp_secret_b32: Mapped[str | None] = mapped_column(String(64))  # base32 secret (no spaces)
    # SMS (optional)
    phone_cc: Mapped[str | None] = mapped_column(String(4))  # e.g., "+91"
    phone_number: Mapped[str | None] = mapped_column(String(20))
    # EMAIL (optional)
    email_override: Mapped[str | None] = mapped_column(CITEXT)

    label: Mapped[str | None] = mapped_column(String(120))
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Store hashed backup codes; rotate on regeneration
    backup_codes_hashes: Mapped[list[str]] = mapped_column(ARRAY(String(128)), nullable=False,
                                                           server_default=text("'{}'"))

    failed_attempts: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(backref="twofa_credentials")

    __table_args__ = (
        # A user can have multiple 2FA methods; but only one active per method if you wish—enforce with partial unique
        Index("ux_twofa_user_method_enabled", "user_id", "method", unique=True, postgresql_where=text("enabled = true and verified_at is not null")),
        Index("ix_twofa_user", "user_id"),
        dict(
            schema="auth",
            comment="User two-factor authentication credentials (TOTP, SMS, Email)",
        )
    )


# ---------- Sessions (refresh tokens or server-side sessions)
class UserSession(TimestampMixin, Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )

    # Store only a hash of refresh token/server session id
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    ip_address: Mapped[str | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(String(512))

    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    user: Mapped["User"] = relationship(backref="sessions")

    __table_args__ = (
        Index("ix_sessions_user", "user_id"),
        Index("ix_sessions_expires", "expires_at"),
        dict(
            schema="auth",
            comment="User sessions or refresh tokens; one active per device/browser",
        )
    )


# ---------- Verification / Reset tokens (short-lived, one table, typed)
class UserToken(TimestampMixin, Base):
    __tablename__ = "user_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False
    )

    purpose: Mapped[TokenPurpose] = mapped_column(SQLEnum(TokenPurpose, name="user_token_purpose"), nullable=False)
    # Store only a hash to avoid leaking secrets if DB is compromised
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)

    # For one-time use tokens
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    user: Mapped["User"] = relationship(backref="tokens")

    __table_args__ = (
        Index("ix_usertokens_user", "user_id"),
        Index("ix_usertokens_purpose", "purpose"),
        Index("ix_usertokens_expires", "expires_at"),
        dict(
            schema="auth",
            comment="Short-lived user tokens for email verification, password reset, etc.",
        )
    )


# ---------- Deleted Users
class DeletedUser(TimestampMixin, Base):
    """
    Archive of users who deleted their account.
    Only store minimal identifying info for audit/compliance.
    """

    __tablename__ = "deleted_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    original_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True)

    email: Mapped[str] = mapped_column(CITEXT, nullable=False)
    first_name: Mapped[str | None] = mapped_column(String(200))
    last_name: Mapped[str | None] = mapped_column(String(200))

    # When deletion occurred
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Why they deleted / system notes (optional)
    reason: Mapped[str | None] = mapped_column(String(255))
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        Index("ix_deleted_users_email", "email"),
        Index("ix_deleted_users_deleted_at", "deleted_at"),
        dict(
            schema="auth",
            comment="Archive of deleted users for audit/compliance; minimal PII only",
        )
    )


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
    author_id: Mapped[int] = mapped_column(ForeignKey("auth.users.id", ondelete="SET NULL"), nullable=True)
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
        dict(
            schema="content",
            comment="Blog posts or articles with markdown content, author, publish state, and full-text search",
        )
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
        conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        conn.execute(sql_text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))


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
