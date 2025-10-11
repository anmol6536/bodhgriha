from __future__ import annotations

import hashlib
import secrets
import string
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Tuple, List, Optional, Sequence

import pyotp
from flask import request, g
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user
from flask import url_for

from forms.user import LoginForm, AddressForm
from models.sql import User, RoleBits, UserSession, TwoFAMethod, TwoFactorCredential, Address, Avatar
from models.yoga.base import YogaSchool
from utilities import LOGGER


ROLE_LABEL_MAP: tuple[tuple[int, str], ...] = (
    (int(RoleBits.MEMBER), "Member"),
    (int(RoleBits.INSTRUCTOR), "Instructor"),
    (int(RoleBits.EDITOR), "Editor"),
    (int(RoleBits.STAFF), "Staff"),
    (int(RoleBits.ADMIN), "Admin"),
)


@dataclass(slots=True)
class AdminUserSummary:
    user: User
    totp_enabled: bool
    is_verified: bool
    addresses: Sequence[Address]
    schools: Sequence[YogaSchool]
    role_labels: Sequence[str]


def _normalize_boolish(value: Any) -> bool:
    """
    Interpret common truthy/falsy representations found in meta payloads.
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if not normalized:
            return False
        return normalized not in {"0", "false", "no", "off", "pending"}
    return bool(value)


def _is_user_verified(user: User) -> bool:
    meta = user.meta or {}
    truthy_keys = (
        "is_verified",
        "verified",
        "email_verified",
        "is_email_verified",
    )
    for key in truthy_keys:
        if key in meta:
            return _normalize_boolish(meta.get(key))

    timestamp_keys = (
        "verified_at",
        "email_verified_at",
        "email_confirmed_at",
    )
    for key in timestamp_keys:
        if meta.get(key):
            return True
    return False


def _apply_admin_user_search_filter(statement, search_field: str | None, search_value: str | None):
    if not search_value:
        return statement

    field = (search_field or "email").lower()
    query = search_value.strip()
    if not query:
        return statement

    if field == "user_id":
        try:
            user_id = int(query)
        except (TypeError, ValueError):
            return statement.where(User.id == -1)
        return statement.where(User.id == user_id)

    if field == "email":
        like_expr = f"%{query}%"
        return statement.where(User.email.ilike(like_expr))

    # Fallback: search email as default.
    like_expr = f"%{query}%"
    return statement.where(User.email.ilike(like_expr))


def list_users_for_admin(
        db: Session,
        *,
        search_field: str | None = None,
        search_value: str | None = None,
        limit: int | None = None,
        offset: int = 0,
) -> list[AdminUserSummary]:
    stmt = (
        select(User)
        .options(selectinload(User.addresses))
        .order_by(User.created_at.desc().nullslast(), User.id.desc())
    )
    stmt = _apply_admin_user_search_filter(stmt, search_field, search_value)

    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)

    users = list(db.scalars(stmt))
    if not users:
        return []

    user_ids = [user.id for user in users]

    totp_user_ids = set(
        db.scalars(
            select(TwoFactorCredential.user_id)
            .where(TwoFactorCredential.user_id.in_(user_ids))
            .where(TwoFactorCredential.method == TwoFAMethod.TOTP)
            .where(TwoFactorCredential.enabled.is_(True))
            .where(TwoFactorCredential.verified_at.isnot(None))
        )
    )

    schools_map: dict[int, list[YogaSchool]] = {uid: [] for uid in user_ids}
    fetched_schools = list(
        db.scalars(
            select(YogaSchool).where(YogaSchool.owner_id.in_(user_ids))
        )
    )
    for school in fetched_schools:
        schools_map.setdefault(school.owner_id, []).append(school)

    summaries: list[AdminUserSummary] = []
    fallback_timestamp = datetime.min.replace(tzinfo=timezone.utc)

    for user in users:
        addresses = sorted(
            list(user.addresses or []),
            key=lambda addr: (
                not getattr(addr, "is_primary", False),
                getattr(addr, "created_at", None) or fallback_timestamp,
            ),
        )
        schools = sorted(
            schools_map.get(user.id, []),
            key=lambda sch: (
                getattr(sch, "created_at", None) or fallback_timestamp,
                sch.id,
            ),
        )
        role_bits_value = int(getattr(user, "role_bits", 0) or 0)
        role_labels = [
            label for bit, label in ROLE_LABEL_MAP if role_bits_value & bit
        ]
        if not role_labels:
            role_labels = ["Member"]

        summaries.append(
            AdminUserSummary(
                user=user,
                totp_enabled=user.id in totp_user_ids,
                is_verified=_is_user_verified(user),
                addresses=tuple(addresses),
                schools=tuple(schools),
                role_labels=tuple(role_labels),
            )
        )

    return summaries


def count_users_for_admin(
        db: Session,
        *,
        search_field: str | None = None,
        search_value: str | None = None,
) -> int:
    stmt = select(func.count()).select_from(User)
    stmt = _apply_admin_user_search_filter(stmt, search_field, search_value)
    return db.scalar(stmt) or 0


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
            LOGGER.warning("2FA required but not provided or invalid for user id=%s email=%s code=%s", user.id, email,
                           totp_code)
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


def _user_exists(db: Session, email: str) -> bool:
    exists = db.scalar(select(User.id).where(User.email == email))
    return bool(exists)


def _generate_recovery_codes(count: int = 10, length: int = 8) -> List[str]:
    alphabet = string.ascii_uppercase + string.digits
    return [''.join(secrets.choice(alphabet) for _ in range(length)) for _ in range(count)]


def setup_totp(
        db: Session,
        user: "User",
        reuse_secret: Optional[str] = None,
        recovery_count: int = 10
) -> Tuple[str, str, List[str]]:
    """
    Ensure a single *pending* TOTP credential exists for `user`, optionally reusing/rotating the secret.

    Returns:
        (provisioning_uri, secret_b32, plain_recovery_codes)

    Notes:
    - Will raise ValueError("TOTP already enabled") if a verified TOTP exists.
    - If reusing an existing pending secret and not rotating, returns [] for recovery codes.
    - Caller must NOT expose the secret or plain codes to clients.
    """
    if user is None:
        raise ValueError("user_not_found")

    # 1) Hard stop if user already has a verified TOTP
    existing_verified = db.scalar(
        select(TwoFactorCredential).where(
            TwoFactorCredential.user_id == user.id,
            TwoFactorCredential.method == TwoFAMethod.TOTP,
            TwoFactorCredential.enabled.is_(True),
            TwoFactorCredential.verified_at.isnot(None),  # verified
        )
    )
    if existing_verified:
        raise ValueError("TOTP already enabled")

    # 2) Look for a pending (enabled, not yet verified) TOTP
    pending = db.scalar(
        select(TwoFactorCredential).where(
            TwoFactorCredential.user_id == user.id,
            TwoFactorCredential.method == TwoFAMethod.TOTP,
            TwoFactorCredential.enabled.is_(True),
            TwoFactorCredential.verified_at.is_(None),  # pending
        )
    )

    # helpers
    def _new_codes(n: int) -> tuple[list[str], list[str]]:
        plain = _generate_recovery_codes(n)
        hashed = [generate_password_hash(c) for c in plain]
        return plain, hashed

    plain_codes: List[str] = []

    if pending:
        # Reuse existing pending credential
        if reuse_secret:
            # rotate secret and regen codes
            pending.totp_secret_b32 = reuse_secret
            plain_codes, hashed = _new_codes(recovery_count)
            pending.backup_codes_hashes = hashed
        else:
            # keep current secret; do not regenerate codes
            plain_codes = []
        secret_b32 = pending.totp_secret_b32

    else:
        # 3) No pending cred -> create one
        secret_b32 = reuse_secret or pyotp.random_base32()
        plain_codes, hashed = _new_codes(recovery_count)
        pending = TwoFactorCredential(
            user_id=user.id,
            method=TwoFAMethod.TOTP,
            totp_secret_b32=secret_b32,
            backup_codes_hashes=hashed,
            enabled=True,
            verified_at=None,
            label="Authenticator App",
        )
        db.add(pending)

    db.flush()  # ensure pending.id is assigned and constraints checked

    # 4) Build otpauth URI from the (reused or new) secret
    provisioning_uri = pyotp.TOTP(secret_b32).provisioning_uri(
        user.email, issuer_name="Bodhgriha"
    )

    return provisioning_uri, secret_b32, plain_codes


def _resolve_user(db: Session, *, email: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        return None
    return user


def _verify_totp(db: Session, user: User, secret: str) -> None:
    # update verified_at if successful
    cred = db.scalar(
        select(TwoFactorCredential)
        .where(TwoFactorCredential.user_id == user.id,
               TwoFactorCredential.totp_secret_b32 == secret,
               TwoFactorCredential.method == TwoFAMethod.TOTP,
               TwoFactorCredential.enabled == True)  # noqa: E712
    )

    cred.verified_at = datetime.now(timezone.utc)
    db.flush()


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


def update_user_avatar(
        db: Session,
        *,
        user_id: int,
        avatar_data: Dict[str, Any],
) -> Avatar:
    """
    Create or replace a user's avatar record and store metadata for cache busting.

    Args:
        db: Active database session.
        user_id: The owner of the avatar.
        avatar_data: Processed image payload from services.content.avatar.prepare_avatar.

    Returns:
        The persisted Avatar instance.
    """
    avatar = db.scalar(select(Avatar).where(Avatar.user_id == user_id))
    if avatar is None:
        avatar = Avatar(user_id=user_id)
        db.add(avatar)

    avatar.content = avatar_data["content"]
    avatar.content_type = avatar_data.get("content_type", "image/webp")
    avatar.size_bytes = avatar_data["size_bytes"]
    avatar.sha256 = avatar_data["sha256"]
    avatar.width = avatar_data.get("width")
    avatar.height = avatar_data.get("height")
    avatar.uploaded_at = datetime.now(timezone.utc)

    user = db.get(User, user_id)
    if user is None:
        raise ValueError("user_not_found")

    meta = dict(user.meta or {})
    meta["avatar_sha256"] = avatar.sha256
    meta["avatar_updated_at"] = avatar.uploaded_at.isoformat()
    user.meta = meta

    db.flush()
    return avatar


def save_address_from_form(
        db: Session,
        *,
        form: AddressForm,
        user_id: int | None = None,
) -> Address:
    """
    Persist an address based on the submitted AddressForm.

    Args:
        db: Active database session.
        form: Validated AddressForm instance.
        user_id: Optional override for the address owner. Falls back to form/user.

    Returns:
        The newly created or updated Address instance.

    Raises:
        ValueError: if the address cannot be resolved for the current user.
    """
    target_user_id = user_id
    if target_user_id is None:
        raw_user_id = form.user_id.data
        if raw_user_id:
            try:
                target_user_id = int(raw_user_id)
            except (TypeError, ValueError) as exc:
                raise ValueError("invalid_user_id") from exc
        elif current_user.is_authenticated:
            target_user_id = current_user.id
        else:
            raise ValueError("user_required")

    address: Address | None = None
    if form.id.data:
        try:
            address_id = int(form.id.data)
        except (TypeError, ValueError) as exc:
            raise ValueError("invalid_address_id") from exc
        address = db.get(Address, address_id)
        if not address or address.user_id != target_user_id:
            raise ValueError("address_not_found")

    if address is None:
        address = Address(user_id=target_user_id)
        db.add(address)

    address.user_id = target_user_id
    address.line1 = (form.line1.data or "").strip()
    address.line2 = (form.line2.data or "").strip() or None
    address.city = (form.city.data or "").strip()
    address.state = (form.state.data or "").strip() or None
    address.postal_code = (form.postal_code.data or "").strip()
    address.country_iso2 = (form.country_iso2.data or "").upper()

    mark_primary = bool(form.is_primary.data)
    if mark_primary:
        query = db.query(Address).filter(Address.user_id == target_user_id, Address.is_primary.is_(True))
        if address.id:
            query = query.filter(Address.id != address.id)
        query.update({"is_primary": False}, synchronize_session=False)

    address.is_primary = mark_primary

    db.flush()

    return address


def dashboard_links() -> List[Dict[str, str]]:
    sidebar = [
        {
            "title": "Account",
            "links": [
                {"label": "Profile", "url": url_for('user.profile')},
                {"label": "Security", "url": "#"},
                {"label": "Bookings", "url": "#"},
                {"label": "Payments", "url": "#"}
            ]
        }
    ]

    if current_user.has_previlige(RoleBits.INSTRUCTOR):
        sidebar.append(
            {
                "title": "Instructor",
                "links": [
                    {"label": "Register New School", "url": url_for('schools.register')}
                ]
            }
        )

    if current_user.has_previlige(RoleBits.ADMIN):
        sidebar.append(
            {
                "title": "Admin",
                "links": [
                    {"label": "School Dashboard", "url": url_for('schools.school_dashboard')},
                    {"label": "Register Blog", "url": url_for('blog.upload')},
                    {"label": "Blog Dashboard", "url": url_for('blog.dashboard')},
                    {"label": "User Management", "url": url_for('admin_users.user_dashboard')},
                ]
            }
        )


    return sidebar


# Ensure user profile modal routes register when the services layer is imported.
try:
    import importlib
    importlib.import_module("views.user.profile")
except ModuleNotFoundError:
    pass
