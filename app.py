from flask import Flask, render_template, send_from_directory, request, redirect, url_for, flash, make_response
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_talisman import Talisman
import os
from models.sql import User, BlogPost
from core.db import uow, init_db
from views import register_views
from core.enum_seed import seed_enums
from flask_login import LoginManager
from sqlalchemy import select
from utilities.logger import configure_logging
from services.base import _context, _invert_navbar_colors
from flask_login import login_required
from services.chat import register_chat



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
        SECRET_KEY=os.environ.get("SECRET_KEY"),
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
            "https://cdn.socket.io",
            "unsafe-inline",  # needed for HTMX
            # "'unsafe-eval'",  # only if you set tailwind.config in-page at runtime
        ],

        # --- Styles ---
        "style-src": [
            "'self'",
            "'unsafe-inline'",  # Tailwind CDN injects <style>
            "data:",
            "https://fonts.googleapis.com",
            "https://fonts.gstatic.com",
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
            "https://fonts.gstatic.com",
            "https://fonts.googleapis.com",
            "data:",
        ],

        # --- XHR / SSE / fetch (HTMX) ---
        "connect-src": [
            "'self'",
            "https://maps.googleapis.com",
            "https://maps.gstatic.com",
            "wss:",
            "ws:",
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

    register_chat(app)  # initialize Flask-SocketIO for chat support

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
        from views.content.listings import Listing
            # Dummy data for listings
        listings = [
            Listing(
                id=1,
                title="4 Day Refreshing Yoga Retreat with Meditation and Guided Walks in Alicante, Costa Blanca, Spain",
                snippet="Experience a rejuvenating 4-day yoga retreat in the serene landscapes of Alicante, Costa Blanca. Enjoy daily yoga sessions, meditation practices, and guided nature walks. Perfect for all levels.",
                href="/retreats/1",
                image_url=url_for('static', filename='images/blog/2.jpeg'),
                image_alt="Retreat group practicing yoga outdoors",
                country="Spain",
                country_flag_emoji="🇪🇸",
                city="Alicante",
                region="Costa Blanca",
                duration_days=4,
                persons=1,
                available_all_year=True,
                perks=["Airport transfer included", "All meals included", "Vegetarian friendly", "Instructed in English"],
                interested_count=28,
                rating_value=4.5,
                rating_count=610,
                price_from=563.0,
                currency="$ USD"
            ),
            Listing(
                id=2,
                title="7 Day Yoga and Wellness Retreat in Bali, Indonesia",
                snippet="Join us for a transformative 7-day yoga and wellness retreat in the heart of Bali. Immerse yourself in daily yoga practices, holistic wellness workshops, and explore the vibrant culture of Bali.",
                href="/retreats/2",
                image_url=url_for('static', filename='images/blog/1.jpeg'),
                image_alt="Yoga session at a beachside retreat",
                country="Indonesia",
                country_flag_emoji="🇮🇩",
                city="Ubud",
                region="Bali",
                duration_days=7,
                persons=1,
                available_all_year=False,
                perks=["Airport transfer included", "All meals included", "Vegan options available", "Instructed in English"],
                interested_count=45,
                rating_value=4.8,
                rating_count=890,
                price_from=1200.0,
                currency="$ USD"
            )
        ]

        return render_template(
            "index.html",
            listings=listings,
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

if __name__ == "__main__":
    from services.chat import socketio

    app = create_app()
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)