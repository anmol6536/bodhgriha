# views/__init__.py
from __future__ import annotations
from flask import Flask


def register_views(app: Flask) -> None:
    """
    Attach all blueprints to the Flask app.
    Keep this as the single entry point for route registration.
    """
    # Admin
    from .admin.user import bp as user_bp
    app.register_blueprint(user_bp, url_prefix="/admin/user")

    # Example: blog blueprint
    from .admin.blog import bp as blog_bp
    app.register_blueprint(blog_bp, url_prefix="/admin/blog")
