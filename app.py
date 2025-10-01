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


def create_app():
    app = Flask(__name__)

    init_db()

    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-not-secure"),
        SESSION_COOKIE_SECURE=True,  # send only over HTTPS
        SESSION_COOKIE_HTTPONLY=True,  # not accessible to JS
        SESSION_COOKIE_SAMESITE="Lax",  # CSRF mitigation for cross-site
        WTF_CSRF_TIME_LIMIT=None,  # optional, disable token timeout
    )

    # --- CSRF protection
    CSRFProtect(app)

    # --- Content Security Policy (no unsafe-inline; use nonce)
    csp = {
        "default-src": "'self'",
        "script-src": ["'self'"],  # nonced scripts will be allowed via talisman nonce helper
        "style-src": ["'self'", "'unsafe-inline'"],  # keep inline styles off if you can; Tailwind often OK
        "img-src": ["'self'", "data:"],  # add your CDN domains if needed
        "font-src": ["'self'"],
        "connect-src": ["'self'"],  # add API domains if needed
        "frame-ancestors": "'none'",  # disallow embedding
        "base-uri": "'self'",
        "form-action": "'self'",
        "object-src": "'none'",
        "upgrade-insecure-requests": "",  # auto-upgrade http->https
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
    login_manager.login_view = "user.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        with uow() as db:
            return db.scalar(select(User).where(User.id == int(user_id)))

    register_views(app)

    @app.route('/')
    def hello():
        return render_template('base.html')

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(
            os.path.join(app.root_path, 'static'),
            'favicon.png',
            mimetype='image/png'
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=9090, ssl_context="adhoc")
