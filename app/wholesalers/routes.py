from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request

from ..decorators import role_required
from ..extensions import db
from ..models import KhataTransaction, Wholesaler

wholesalers_bp = Blueprint("wholesalers", __name__, url_prefix="/api/wholesalers")

KHATA_TYPES = ("debt", "uchanti")
ENTRY_TYPES = ("add", "deduct")


@wholesalers_bp.get("")
@role_required("admin", "staff")
def list_wholesalers():
    items = Wholesaler.query.order_by(Wholesaler.name.asc()).all()
    return jsonify(
        wholesalers=[w.to_dict() for w in items],
        totals={
            "debt": float(sum(w.debt_khata or Decimal(0) for w in items)),
            "uchanti": float(sum(w.uchanti_khata or Decimal(0) for w in items)),
        },
    )


@wholesalers_bp.post("")
@role_required("admin")
def create_wholesaler():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify(error="name is required"), 400
    w = Wholesaler(
        name=name,
        phone=(data.get("phone") or "").strip() or None,
        address=(data.get("address") or "").strip() or None,
    )
    db.session.add(w)
    db.session.commit()
    return jsonify(wholesaler=w.to_dict()), 201


@wholesalers_bp.put("/<int:wid>")
@role_required("admin")
def update_wholesaler(wid):
    w = db.session.get(Wholesaler, wid)
    if not w:
        return jsonify(error="Wholesaler not found"), 404
    data = request.get_json(force=True) or {}
    if "name" in data:
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify(error="name cannot be empty"), 400
        w.name = name
    if "phone" in data:
        w.phone = (data.get("phone") or "").strip() or None
    if "address" in data:
        w.address = (data.get("address") or "").strip() or None
    db.session.commit()
    return jsonify(wholesaler=w.to_dict())


@wholesalers_bp.delete("/<int:wid>")
@role_required("admin")
def delete_wholesaler(wid):
    w = db.session.get(Wholesaler, wid)
    if not w:
        return jsonify(error="Wholesaler not found"), 404
    db.session.delete(w)
    db.session.commit()
    return jsonify(message="Wholesaler deleted")


@wholesalers_bp.post("/<int:wid>/khata")
@role_required("admin")
def update_khata(wid):
    """Add or deduct from a wholesaler's debt khata or uchanti khata."""
    w = db.session.get(Wholesaler, wid)
    if not w:
        return jsonify(error="Wholesaler not found"), 404
    data = request.get_json(force=True) or {}
    khata_type = data.get("khata_type")
    entry_type = data.get("entry_type")
    if khata_type not in KHATA_TYPES:
        return jsonify(error=f"khata_type must be one of {KHATA_TYPES}"), 400
    if entry_type not in ENTRY_TYPES:
        return jsonify(error=f"entry_type must be one of {ENTRY_TYPES}"), 400
    try:
        amount = Decimal(str(data.get("amount") or 0))
    except (TypeError, ValueError, InvalidOperation):
        return jsonify(error="amount must be a number"), 400
    if amount <= 0:
        return jsonify(error="amount must be greater than 0"), 400

    balance = w.debt_khata if khata_type == "debt" else w.uchanti_khata
    balance = Decimal(balance)
    new_balance = balance + amount if entry_type == "add" else balance - amount
    if new_balance < 0:
        return jsonify(error="Khata balance would go negative"), 400

    if khata_type == "debt":
        w.debt_khata = new_balance
    else:
        w.uchanti_khata = new_balance

    tx = KhataTransaction(
        wholesaler_id=w.id,
        khata_type=khata_type,
        entry_type=entry_type,
        amount=amount,
        balance_after=new_balance,
        note=(data.get("note") or "").strip() or None,
        created_by=g.current_user.id,
    )
    db.session.add(tx)
    db.session.commit()
    return jsonify(wholesaler=w.to_dict(), transaction=tx.to_dict())


@wholesalers_bp.get("/<int:wid>/khata-history")
@role_required("admin", "staff")
def khata_history(wid):
    w = db.session.get(Wholesaler, wid)
    if not w:
        return jsonify(error="Wholesaler not found"), 404
    txs = (
        KhataTransaction.query.filter_by(wholesaler_id=wid)
        .order_by(KhataTransaction.created_at.desc(), KhataTransaction.id.desc())
        .all()
    )
    return jsonify(
        wholesaler=w.to_dict(),
        transactions=[t.to_dict() for t in txs],
    )
