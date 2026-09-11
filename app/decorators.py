from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, jwt_required

from .extensions import db
from .models import User


def role_required(*roles):
    """JWT auth + role check. Sets g.current_user for the route handler."""

    def wrapper(fn):
        @wraps(fn)
        @jwt_required()
        def inner(*args, **kwargs):
            user = db.session.get(User, int(get_jwt_identity()))
            if not user or not user.is_active:
                return jsonify(error="Account is disabled or missing"), 403
            if user.role not in roles:
                return jsonify(error="You do not have permission to do that"), 403
            g.current_user = user
            return fn(*args, **kwargs)

        return inner

    return wrapper


def notify_admins(title, message):
    """Create a notification row for every active admin."""
    from .models import Notification

    admins = User.query.filter_by(role="admin", is_active=True).all()
    for admin in admins:
        db.session.add(Notification(user_id=admin.id, title=title, message=message))
    db.session.commit()
    return len(admins)
