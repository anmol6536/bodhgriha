from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

from models.sql import User, RoleBits  # BlogPost unused here


def add_user(
        db: Session,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role_bits: int | RoleBits = RoleBits.MEMBER,
        meta: Dict[str, Any] | None = None,
) -> User:
    """
    Create a new user with a hashed password.
    Raises ValueError('email_exists') if email already taken.
    """
    # Fast existence check (avoids IntegrityError round-trip)
    exists = db.scalar(select(User.id).where(User.email == email))
    if exists:
        raise ValueError("email_exists")

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        role_bits=int(role_bits),
        meta=meta or {},
    )
    db.add(user)
    try:
        db.flush()  # assigns user.id without committing the transaction
    except IntegrityError as ie:
        # Race condition on unique email
        db.rollback()
        raise ValueError("email_exists") from ie
    return user


def get_user(db: Session, *, email: str, password: str) -> Optional[User]:
    """
    Look up user by email and verify password.
    Returns User if credentials are valid, else None.
    """
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        return None
    if not check_password_hash(user.password_hash, password):
        return None
    return user


def _resolve_user(db: Session, *, email: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        return None
    return user
