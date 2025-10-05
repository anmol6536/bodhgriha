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
    # The testimonials blueprint already has url_prefix="/testimonials"
    # Avoid double-prefixing by not passing url_prefix here.
    app.register_blueprint(testimonials_bp)
