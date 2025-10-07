from functools import wraps
from flask import abort
from flask_login import current_user
from models.sql.base import RoleBits


def role_validation(required_roles: str):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # This should be handled by @login_required, but as a safeguard
                return abort(401)
            
            # if role is higher than required, allow access
            if not current_user.has_previlige(RoleBits[required_roles]):
                return abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
