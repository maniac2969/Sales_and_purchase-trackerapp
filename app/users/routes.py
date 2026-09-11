from flask import Blueprint, g, jsonify, request

from ..decorators import role_required
from ..extensions import db
from ..models import User

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

ROLES = ("admin", "staff")


@users_bp.get("")
@role_required("admin")
def list_users():
    users = User.query.order_by(User.role.asc(), User.name.asc()).all()
    return jsonify(users=[u.to_dict() for u in users])


@users_bp.post("")
@role_required("admin")
def create_user():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or "staff"
    if not name or not username or not password:
        return jsonify(error="name, username and password are required"), 400
    if len(password) < 4:
        return jsonify(error="password must be at least 4 characters"), 400
    if role not in ROLES:
        return jsonify(error=f"role must be one of {ROLES}"), 400
    if User.query.filter_by(username=username).first():
        return jsonify(error="username is already taken"), 409

    user = User(name=name, username=username, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify(user=user.to_dict()), 201


@users_bp.put("/<int:user_id>")
@role_required("admin")
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(error="User not found"), 404
    data = request.get_json(force=True) or {}

    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify(error="name cannot be empty"), 400
        user.name = name
    if "role" in data and data["role"] in ROLES:
        if user_id == g.current_user.id and data["role"] != "admin":
            return jsonify(error="You cannot demote your own account"), 400
        user.role = data["role"]
    if "password" in data and data["password"]:
        if len(data["password"]) < 4:
            return jsonify(error="password must be at least 4 characters"), 400
        user.set_password(data["password"])
    if "is_active" in data:
        if user_id == g.current_user.id and not data["is_active"]:
            return jsonify(error="You cannot disable your own account"), 400
        user.is_active = bool(data["is_active"])
    db.session.commit()
    return jsonify(user=user.to_dict())


@users_bp.delete("/<int:user_id>")
@role_required("admin")
def delete_user(user_id):
    if user_id == g.current_user.id:
        return jsonify(error="You cannot delete your own account"), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(error="User not found"), 404
    db.session.delete(user)
    db.session.commit()
    return jsonify(message="User deleted")
