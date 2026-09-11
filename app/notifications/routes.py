from flask import Blueprint, g, jsonify

from ..decorators import role_required
from ..extensions import db
from ..models import Notification

notifications_bp = Blueprint(
    "notifications", __name__, url_prefix="/api/notifications"
)


@notifications_bp.get("")
@role_required("admin", "staff")
def list_notifications():
    items = (
        Notification.query.filter_by(user_id=g.current_user.id)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(50)
        .all()
    )
    unread = (
        Notification.query.filter_by(user_id=g.current_user.id, is_read=False)
        .count()
    )
    return jsonify(notifications=[n.to_dict() for n in items], unread_count=unread)


@notifications_bp.post("/<int:nid>/read")
@role_required("admin", "staff")
def mark_read(nid):
    n = db.session.get(Notification, nid)
    if not n or n.user_id != g.current_user.id:
        return jsonify(error="Notification not found"), 404
    n.is_read = True
    db.session.commit()
    return jsonify(notification=n.to_dict())


@notifications_bp.post("/read-all")
@role_required("admin", "staff")
def mark_all_read():
    Notification.query.filter_by(
        user_id=g.current_user.id, is_read=False
    ).update({"is_read": True})
    db.session.commit()
    return jsonify(message="All notifications marked as read")
