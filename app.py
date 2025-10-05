from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash, make_response
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_talisman import Talisman
import os
from core.db import init_db
from models.sql import User, BlogPost
from views import register_views
from flask_login import LoginManager
from sqlalchemy import select
from core.db import uow
from core.enum_seed import seed_enums
from utilities.logger import configure_logging
from services.base import _context, _invert_navbar_colors


def create_app():
    app = Flask(__name__)
    app.config.logger = configure_logging(app.config.get("LOG_LEVEL", "DEBUG"))
    app.config['STATIC_FOLDER'] = 'static'

    init_db()  # create tables if not exist (dev only; use Alembic in prod)
    app.config.logger.info("Database initialized.")

    app.config.logger.info("Seeding enumeration tables...")
    with uow() as db:
        seed_enums(db)
    app.config.logger.info("Enumeration tables seeded.")

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-not-secure"),
        SESSION_COOKIE_SECURE=True,  # send only over HTTPS
        SESSION_COOKIE_HTTPONLY=True,  # not accessible to JS
        SESSION_COOKIE_SAMESITE="Lax",  # CSRF mitigation for cross-site
        WTF_CSRF_TIME_LIMIT=None,  # optional, disable token timeout
        SITE_NAME="Bodhgriha"
    )

    # --- CSRF protection
    CSRFProtect(app)

    # --- Content Security Policy (no unsafe-inline; use nonce)
    csp = {
        # --- Defaults & hardening ---
        "default-src": "'self'",
        "base-uri": "'self'",
        "form-action": "'self'",
        "frame-ancestors": "'none'",
        "object-src": "'none'",
        "script-src-attr": "'none'",
        "upgrade-insecure-requests": "",

        # --- Scripts (Tailwind CDN + HTMX) ---
        "script-src": [
            "'self'",
            # nonced inline scripts allowed via Talisman (nonce injected)
            "https://cdn.tailwindcss.com",
            "https://unpkg.com",
            "unsafe-inline",  # needed for HTMX
            # "'unsafe-eval'",  # only if you set tailwind.config in-page at runtime
        ],

        # --- Styles ---
        "style-src": [
            "'self'",
            "'unsafe-inline'",  # Tailwind CDN injects <style>
            "https:",
            "data:",
            "https://fonts.googleapis.com",  # drop if not using Google Fonts
        ],

        # --- Images (QR/data URIs ok) ---
        "img-src": [
            "'self'",
            "data:",
            "blob:",
            "https:",
        ],

        # --- VIDEO/AUDIO (add this for your background video) ---
        "media-src": [
            "'self'",
            "https:",  # keep if you might host video on a CDN later
            "data:",  # rare, but harmless
            "blob:",  # needed only if you ever use blob URLs
        ],

        # --- Fonts ---
        "font-src": [
            "'self'",
            "https://fonts.gstatic.com",  # drop if not using Google Fonts
            "data:",
        ],

        # --- XHR / SSE / fetch (HTMX) ---
        "connect-src": [
            "'self'",
            "https://maps.googleapis.com",
            "https://maps.gstatic.com",
        ],

        # --- Frames (for <iframe> embeds like Google Maps) ---
        "frame-src": [
            "'self'",
            "https://www.google.com",
            "https://maps.google.com",
            "https://www.google.com/maps",
        ],

        # (Optional) lock these harder if you’re not using them:
        # "frame-src": "'none'",
        # "worker-src": ["'self'", "blob:"],
    }

    # --- Talisman security headers
    Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=["script-src"],
        force_https=False,  # redirects http->https
        strict_transport_security=True,
        strict_transport_security_max_age=31536000,
        strict_transport_security_include_subdomains=True,
        strict_transport_security_preload=True,
        frame_options="DENY",
        referrer_policy="strict-origin-when-cross-origin",
        permissions_policy={
            "geolocation": "()",
            "camera": "()",
            "microphone": "()",
            "fullscreen": "()",
        },
        session_cookie_secure=True,
    )

    # --- Login manager
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with uow() as db:
            return db.scalar(select(User).where(User.id == int(user_id)))

    register_views(app)

    @app.route('/')
    def index():
        from utilities.navbar_loader import get_navbar_context
        return render_template(
            "index.html",
            **_context()
        )

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'icons/icon.png', mimetype='image/png')

    @app.route('/manifest.json')
    def manifest():
        return send_from_directory(app.static_folder, 'manifest.json')

    @app.route('/robots.txt')
    def robots_txt():
        return send_from_directory(app.static_folder, 'robots.txt', mimetype='text/plain')

    @app.route('/about-us')
    def about_us():
        return render_template(
            "about.html",
            **_invert_navbar_colors(_context())
        )

    @app.route('/testimonials', methods=['GET', 'POST'])
    def testimonials():
        # This route can be used for testimonials management if needed
        # For now, redirect to home page
        return redirect(url_for('index'))

    return app


app = create_app()