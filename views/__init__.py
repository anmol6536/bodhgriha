# views/__init__.py
from __future__ import annotations
from flask import Flask


def register_views(app: Flask) -> None:
    """
    Attach all blueprints to the Flask app.
    Keep this as the single entry point for route registration.
    """
    # Example: blog blueprint
    from .blog.base import bp as blog_bp
    app.register_blueprint(blog_bp, url_prefix="/blog")

    # Auth
    from .auth.user import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    # UI
    from .ui.base import bp as ui_bp
    app.register_blueprint(ui_bp, url_prefix="/ui")

    # Admin - Users
    from .admin.school import bp as school_bp
    app.register_blueprint(school_bp, url_prefix="/admin/schools")
    
    from .content.testimonials import bp as testimonials_bp
    app.register_blueprint(testimonials_bp, url_prefix="/testimonials")

    # Legal
    from .legal.base import bp as legal_bp
    app.register_blueprint(legal_bp, url_prefix="/legal")

    from .content.listings import bp as listings_bp
    app.register_blueprint(listings_bp, url_prefix="/search")

    # User Dashboard
    from .user.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix="/dashboard")

    # Chat
    from .content.chat import bp as chat_bp
    app.register_blueprint(chat_bp, url_prefix="/chat")
