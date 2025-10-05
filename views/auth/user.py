import base64
import qrcode
from datetime import datetime, timedelta, timezone
from io import BytesIO

from flask import (
    Blueprint, render_template, request, flash, session, redirect, url_for, make_response
)
from flask_login import login_required, current_user
from flask_login import login_user, logout_user

from core.db import uow
from forms.user import LoginForm, SignupForm
from services.user import add_user
from services.user import get_user, _user_exists
from services.user import (
    setup_totp as issue_totp_secret,
    validate_totp_or_recovery,
    _verify_totp
)
from utilities.logger import configure_logging
from services.base import _context

LOG = configure_logging()

bp = Blueprint("auth", __name__)
PENDING_TOTP_KEY = "pending_totp_secret"
PENDING_TOTP_EXP = "pending_totp_expires"


# ========== User Registration ==========

@bp.route("/signup", methods=["GET", "POST"])
@bp.route("/register", methods=["GET", "POST"])
def register():
    form = SignupForm()
    if form.validate_on_submit():
        LOG.info(f"Registering user with email: {form.email.data}")
        with uow() as db:
            if _user_exists(db, form.email.data):
                flash("Email already registered. Please log in.", "warning")
                LOG.critical(f"Attempt to register with existing email: {form.email.data}")
                return redirect(url_for("auth.login"))

            LOG.info(f"Adding new user with email: {form.email.data}")
            add_user(
                db,
                email=form.email.data,
                password=form.password.data,
                first_name=form.first_name.data,
                last_name=form.last_name.data,
            )
            LOG.info(f"User registered successfully with email: {form.email.data}")
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("auth.login"))
    return render_template("user/signup.html", form=form, **_context())


# ========== TOTP 2FA Setup ==========

def _utcnow():
    return datetime.now(timezone.utc)


def _store_pending_secret(secret: str, ttl_sec: int = 300):
    session[PENDING_TOTP_KEY] = secret
    session[PENDING_TOTP_EXP] = (_utcnow() + timedelta(seconds=ttl_sec)).isoformat()


def _get_pending_secret():
    secret = session.get(PENDING_TOTP_KEY)
    exp_iso = session.get(PENDING_TOTP_EXP)
    if not secret or not exp_iso:
        return None
    if _utcnow() > datetime.fromisoformat(exp_iso):
        session.pop(PENDING_TOTP_KEY, None)
        session.pop(PENDING_TOTP_EXP, None)
        return None
    return secret


def _clear_pending_secret():
    session.pop(PENDING_TOTP_KEY, None)
    session.pop(PENDING_TOTP_EXP, None)


def _qr_b64_from_uri(uri: str) -> str:
    buf = BytesIO()
    qrcode.make(uri).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


@bp.route("/setup/mfa", methods=["GET", "POST"])
@login_required
def setup_totp():
    from forms.user import RegisterTOTPForm  # import where you define it
    form = RegisterTOTPForm()

    # If POST, validate token against server-side secret; do not trust hidden field
    if request.method == "POST":
        if form.validate_on_submit():
            pending_secret = _get_pending_secret()
            if not pending_secret:
                flash("Setup window expired. Please restart TOTP setup.", "warning")
                return redirect(url_for(".setup_totp"))

            with uow() as db:
                # validate token (TOTP or recovery), then persist enabling with the server secret
                if validate_totp_or_recovery(db, current_user, form.token.data):
                    _verify_totp(db, current_user, pending_secret)
                    _clear_pending_secret()
                    flash("Two-factor authentication enabled.", "success")
                    return render_template("user/2fa/status.html", status=200, **_context())
                else:
                    flash("Invalid code. Please try again.", "danger")

    # GET or re-render after invalid POST:
    try:
        with uow() as db:
            # If there is already a pending, reuse it within window; otherwise issue a new one
            secret = _get_pending_secret()
            if not secret:
                uri, secret, _ = issue_totp_secret(db, current_user)
                _store_pending_secret(secret, ttl_sec=300)
            else:
                # Rebuild URI from your service if needed; or store URI alongside secret
                uri, _, _ = issue_totp_secret(db, current_user, reuse_secret=secret)
    except ValueError as e:
        if e.args and e.args[0] == "TOTP already enabled":
            flash("TOTP is already enabled for your account.", "info")
            return render_template("user/2fa/status.html", status=200, **_context())
        raise

    # NEVER log secrets/URIs
    qr_b64 = _qr_b64_from_uri(uri)

    # Do not send secret back to client; keep only in session
    # form.secret.data = ""  # if you still have a HiddenField, keep it empty

    resp = make_response(render_template("user/2fa/register.html", form=form, qr_b64=qr_b64, **_context()))
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ========== Login / Logout ==========


@bp.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        with uow() as db:
            user = get_user(db, form=form)
            if user:
                # Example: Set session variable for logged-in user
                login_user(user, remember=form.remember_me.data)
                flash("Login successful.", "success")
                return redirect(url_for("index"))
            else:
                flash("Invalid email or password.", "danger")
                return redirect(url_for("index"))
    return render_template("user/login.html", form=form, page_bg_video_url=url_for("static", filename="login-bg.mp4"), **_context())


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))
