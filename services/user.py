from __future__ import annotations

from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app
from forms.user import LoginForm
from models.sql import User, RoleBits, UserSession, TwoFAMethod, TwoFactorCredential
import pyotp
import qrcode
import secrets
import string
from typing import Tuple, List
from datetime import datetime, timezone, timedelta
import secrets, hashlib
from flask import request, g
from utilities import LOGGER


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
        LOGGER.error("Email already registered: %s", email)
        raise ValueError("email_exists")

    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        first_name=first_name,
        last_name=last_name,
        role_bits=int(role_bits),
        meta=meta or {},
    )
    LOGGER.info("Creating user: %s", email)
    db.add(user)
    try:
        db.flush()  # assigns user.id without committing the transaction
        LOGGER.info("Created user id=%s email=%s", user.id, email)
    except IntegrityError as ie:
        # Race condition on unique email
        db.rollback()
        LOGGER.error("Email already registered")
        raise ValueError("email_exists") from ie
    return user


def get_user(db: Session, *, form: LoginForm) -> Optional[User]:
    email = form.email.data
    password = form.password.data
    totp_code = form.totp_code.data
    remember_me = form.remember_me.data

    # 0) If a valid session cookie already exists and matches this email, trust it.
    existing_raw = request.cookies.get("session")
    if existing_raw:
        print("Existing session cookie found")
        user = authenticate_session(db, existing_raw)
        if user and user.email.lower() == email.lower():
            LOGGER.info("Existing session cookie valid for user id=%s email=%s", user.id, email)
            return user  # already authenticated on this device for this user

    # 1) Password check
    user = db.scalar(select(User).where(User.email == email))
    if not user or not check_password_hash(user.password_hash, password):
        return None
    print("HR")
    LOGGER.info("Password verified for user id=%s email=%s", user.id, email)

    # 2) 2FA check (if enabled)
    has_totp = db.scalar(
        select(TwoFactorCredential.id)
        .where(TwoFactorCredential.user_id == user.id,
               TwoFactorCredential.method == TwoFAMethod.TOTP,
               TwoFactorCredential.enabled == True)  # noqa: E712
    )
    if has_totp:
        if not totp_code or not validate_totp_or_recovery(db, user, totp_code):
            return None
        LOGGER.info("2FA verified for user id=%s email=%s", user.id, email)

    # 3) Issue a session (cookie is set by the view using g.new_session_token)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent")

    ttl_hours = 24 * 30 if remember_me else 24 * 7  # 30 days vs 7 days
    raw_token, _ = issue_session(db, user, ttl_hours, ip, ua)

    # Expose the token to the caller without changing return type
    g.new_session_token = raw_token
    g.new_session_ttl_seconds = ttl_hours * 3600

    return user


def _generate_recovery_codes(count: int = 10, length: int = 8) -> List[str]:
    alphabet = string.ascii_uppercase + string.digits
    return [''.join(secrets.choice(alphabet) for _ in range(length)) for _ in range(count)]


def setup_totp(db: Session, user: User, recovery_count: int = 10) -> Tuple[str, List[str]]:
    """
    Create and persist a TOTP credential for `user`.
    Returns (provisioning_uri, plain_recovery_codes).
    NOTE: Does NOT return the secret. Caller can render QR from URI.
    """
    if user is None:
        raise ValueError("user_not_found")

    # Enforce single enabled TOTP per user (if you have a partial-unique idx)
    existing = db.scalar(
        select(TwoFactorCredential)
        .where(TwoFactorCredential.user_id == user.id,
               TwoFactorCredential.method == TwoFAMethod.TOTP,
               TwoFactorCredential.enabled == True)  # noqa: E712
    )
    if existing:
        raise ValueError("TOTP already enabled")

    totp_secret = pyotp.random_base32()
    plain_codes = _generate_recovery_codes(recovery_count)
    hashed_codes = [generate_password_hash(c) for c in plain_codes]

    cred = TwoFactorCredential(
        user_id=user.id,  # link to user
        method=TwoFAMethod.TOTP,
        totp_secret_b32=totp_secret,
        backup_codes_hashes=hashed_codes,
        enabled=True,
        verified_at=None,
        label="Authenticator App",
    )
    db.add(cred)
    db.flush()  # persist cred.id; not strictly needed but good to surface errors now

    provisioning_uri = pyotp.TOTP(totp_secret).provisioning_uri(
        user.email, issuer_name="Bodhgriha"
    )
    return provisioning_uri, plain_codes


def _resolve_user(db: Session, *, email: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        return None
    return user


def validate_totp_or_recovery(db: Session, user: User, code: str) -> bool:
    cred = db.scalar(
        select(TwoFactorCredential)
        .where(TwoFactorCredential.user_id == user.id,
               TwoFactorCredential.method == TwoFAMethod.TOTP,
               TwoFactorCredential.enabled == True)  # noqa: E712
    )
    if not cred or not cred.totp_secret_b32:
        return False

    # First try TOTP
    if code.isdigit() and pyotp.TOTP(cred.totp_secret_b32).verify(code, valid_window=1):
        cred.last_used_at = datetime.now(timezone.utc)
        db.flush()
        return True

    # Then try recovery codes (one-time use)
    for h in list(cred.backup_codes_hashes or []):
        if check_password_hash(h, code):
            # consume code
            remaining = [x for x in cred.backup_codes_hashes if x != h]
            cred.backup_codes_hashes = remaining
            cred.last_used_at = datetime.now(timezone.utc)
            db.flush()
            return True
    return False


def _hash_token(raw: str) -> str:
    # Use a fast hash only for lookup; the token itself is random & unguessable.
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def issue_session(db, user, ttl_hours: int, ip: str | None, ua: str | None) -> tuple[str, UserSession]:
    raw = secrets.token_urlsafe(48)  # ~288 bits
    token_hash = _hash_token(raw)
    sess = UserSession(
        user_id=user.id,
        token_hash=token_hash,
        issued_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        ip_address=ip,
        user_agent=ua,
        meta={}
    )
    db.add(sess)
    db.flush()  # ensure unique constraint is checked now
    LOGGER.info("Issued session id=%s for user id=%s", sess.id, user.id)
    return raw, sess


def authenticate_session(db, raw_token: str) -> User | None:
    if not raw_token:
        return None
    token_hash = _hash_token(raw_token)
    now = datetime.now(timezone.utc)
    sess = db.scalar(
        select(UserSession)
        .where(UserSession.token_hash == token_hash,
               UserSession.revoked_at.is_(None),
               UserSession.expires_at > now)
    )

    if not sess:
        return None
    # Optionally update last-used timestamp in meta (avoid hot writes on every call)
    return db.get(User, sess.user_id)


def revoke_session(db, raw_token: str) -> bool:
    token_hash = _hash_token(raw_token)
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == token_hash,
                                               UserSession.revoked_at.is_(None)))
    if not sess:
        return False
    sess.revoked_at = datetime.now(timezone.utc)
    db.flush()
    return True


def rotate_session(db, raw_token: str, ttl_hours_new: int, ip: str | None, ua: str | None) -> str | None:
    user = authenticate_session(db, raw_token)
    if not user:
        return None
    # Revoke old
    revoke_session(db, raw_token)
    # Issue new
    new_raw, _ = issue_session(db, user, ttl_hours=ttl_hours_new, ip=ip, ua=ua)
    return new_raw


def forced_update_password(db: Session, user: User, new_password: str) -> None:
    """
    Forcefully reset a user's password (no old password required).
    Intended for admin resets, hard security events, or password-recovery flows.

    Side effects:
    - Hashes and updates the password.
    - Revokes all active sessions for this user (recommended for security).
    - Commits must be done by the caller.
    """
    # Update password hash
    user.password_hash = generate_password_hash(new_password)

    # Revoke all active sessions for this user
    from sqlalchemy import func
    db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.revoked_at.is_(None)
    ).update({"revoked_at": func.now()})

    db.add(user)
    db.flush()


def reset_password(db: Session, email: str, old_password: str, new_password: str) -> None:
    """
    Reset a user's password given the old password.
    Raises ValueError('user_not_found') if user does not exist.
    Raises ValueError('incorrect_password') if old password does not match.
    """
    user = _resolve_user(db, email=email)
    if not user:
        raise ValueError("user_not_found")

    if not check_password_hash(user.password_hash, old_password):
        raise ValueError("incorrect_password")

    forced_update_password(db, user, new_password)



if __name__ == "__main__":
    from core.db import uow, init_db

    init_db()

    with uow() as db:
        try:
            email = "gorakshakar.a@gmail.com"
            # add_user(
            #     db,
            #     email=email,
            #     password="StrongPassword123!",
            #     first_name="Utkarsha",
            #     last_name="Ajgoanakar",
            #     role_bits=RoleBits.ADMIN | RoleBits.MEMBER,  # Admin
            # )

            # user = _resolve_user(db, email=email)
            # provisioning_uri, plain_codes = setup_totp(db, user)
            #
            # qr = qrcode.make(provisioning_uri)
            # qr.show()  # Display the QR code for scanning

            # totp_code = input("Enter TOTP code: ")
            # if validate_totp_or_recovery(db, user, totp_code):
            #     print("TOTP code is valid.")
            # else:
            #     print("Invalid TOTP code.")
            user = _resolve_user(db, email=email)
            forced_update_password(db, user, "open")


            CODE = input("Enter TOTP code: ")
            form = type('LoginForm', (object,), {"email": None, "password": None, "totp_code": None, "remember_me": None})  # Mocking form
            form.email = type('obj', (object,), {'data': email})  # Mocking form data
            form.password = type('obj', (object,), {'data': "open"})  # Replace with actual password
            form.totp_code = type('obj', (object,), {'data': CODE})  # Replace with actual TOTP code if needed
            form.remember_me = type('obj', (object,), {'data': True})  # or False

            user = get_user(db, form=form)

        except ValueError as ve:
            print("Error:", ve)
