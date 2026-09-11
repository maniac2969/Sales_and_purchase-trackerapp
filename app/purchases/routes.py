from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request

from ..decorators import notify_admins, role_required
from ..extensions import db
from ..models import KhataTransaction, Purchase, Wholesaler

purchases_bp = Blueprint("purchases", __name__, url_prefix="/api/purchases")


def _parse_date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return default


@purchases_bp.get("")
@role_required("admin", "staff")
def list_purchases():
    target = _parse_date(request.args.get("date"), date.today())
    items = (
        Purchase.query.filter_by(purchase_date=target)
        .order_by(Purchase.id.asc())
        .all()
    )
    approved = [p for p in items if p.status == "approved"]
    return jsonify(
        date=target.isoformat(),
        purchases=[p.to_dict() for p in items],
        totals={
            "count": len(approved),
            "pieces": sum(p.piece for p in approved),
            "amount": float(sum(p.total_price or Decimal(0) for p in approved)),
        },
    )


@purchases_bp.post("")
@role_required("admin", "staff")
def create_purchase():
    data = request.get_json(force=True) or {}
    wholesaler = db.session.get(Wholesaler, int(data.get("wholesaler_id") or 0))
    if not wholesaler:
        return jsonify(error="wholesaler_id is invalid"), 400
    item = (data.get("item") or "").strip()
    if not item:
        return jsonify(error="item is required"), 400
    try:
        piece = int(data.get("piece") or 0)
        total_price = Decimal(str(data.get("total_price") or 0))
    except (TypeError, ValueError, InvalidOperation):
        return jsonify(error="piece and total_price must be numbers"), 400
    if piece <= 0 or total_price < 0:
        return jsonify(error="piece must be greater than 0"), 400

    is_staff = g.current_user.role == "staff"
    purchase = Purchase(
        wholesaler_id=wholesaler.id,
        item=item,
        piece=piece,
        total_price=total_price,
        purchase_date=_parse_date(data.get("purchase_date"), date.today()),
        on_credit=bool(data.get("on_credit", False)),
        notes=(data.get("notes") or "").strip() or None,
        created_by=g.current_user.id,
        status="pending" if is_staff else "approved",
    )
    db.session.add(purchase)

    if not is_staff and purchase.on_credit:
        _apply_debt(purchase, wholesaler, g.current_user.id)

    db.session.commit()

    if is_staff:
        notify_admins(
            "New purchase awaiting approval",
            f"{g.current_user.name} bought from {wholesaler.name}: "
            f"{item} x {piece} = Rs. {total_price}"
            + (" (on credit)" if purchase.on_credit else ""),
        )
    return jsonify(purchase=purchase.to_dict()), 201


def _apply_debt(purchase, wholesaler, user_id=None):
    """On-credit purchase increases the wholesaler's debt khata."""
    new_balance = Decimal(wholesaler.debt_khata) + Decimal(purchase.total_price)
    wholesaler.debt_khata = new_balance
    db.session.add(
        KhataTransaction(
            wholesaler_id=wholesaler.id,
            khata_type="debt",
            entry_type="add",
            amount=Decimal(purchase.total_price),
            balance_after=new_balance,
            note=f"Purchase #{purchase.id}: {purchase.item}",
            created_by=user_id or purchase.created_by,
        )
    )


@purchases_bp.get("/pending")
@role_required("admin")
def pending_purchases():
    items = (
        Purchase.query.filter_by(status="pending")
        .order_by(Purchase.created_at.asc())
        .all()
    )
    return jsonify(purchases=[p.to_dict() for p in items])


@purchases_bp.post("/<int:purchase_id>/approve")
@role_required("admin")
def approve_purchase(purchase_id):
    purchase = db.session.get(Purchase, purchase_id)
    if not purchase:
        return jsonify(error="Purchase not found"), 404
    purchase.status = "approved"
    if purchase.on_credit:
        _apply_debt(purchase, purchase.wholesaler, g.current_user.id)
    db.session.commit()
    return jsonify(purchase=purchase.to_dict())


@purchases_bp.post("/<int:purchase_id>/reject")
@role_required("admin")
def reject_purchase(purchase_id):
    purchase = db.session.get(Purchase, purchase_id)
    if not purchase:
        return jsonify(error="Purchase not found"), 404
    purchase.status = "rejected"
    db.session.commit()
    return jsonify(purchase=purchase.to_dict())


@purchases_bp.put("/<int:purchase_id>")
@role_required("admin")
def update_purchase(purchase_id):
    purchase = db.session.get(Purchase, purchase_id)
    if not purchase:
        return jsonify(error="Purchase not found"), 404

    data = request.get_json(force=True) or {}
    wholesaler = purchase.wholesaler

    item = (data.get("item") or "").strip()
    if item:
        purchase.item = item

    try:
        if "piece" in data:
            piece = int(data["piece"])
            if piece > 0:
                purchase.piece = piece
        if "total_price" in data:
            new_price = Decimal(str(data["total_price"]))
            if new_price < 0:
                return jsonify(error="total_price must be non-negative"), 400

            if purchase.status == "approved" and purchase.on_credit:
                diff = new_price - purchase.total_price
                wholesaler.debt_khata += diff
                db.session.add(KhataTransaction(
                    wholesaler_id=wholesaler.id,
                    khata_type="debt",
                    entry_type="add" if diff > 0 else "deduct",
                    amount=abs(diff),
                    balance_after=wholesaler.debt_khata,
                    note=f"Adjustment for Purchase #{purchase.id}",
                    created_by=g.current_user.id
                ))
            purchase.total_price = new_price
    except (TypeError, ValueError, InvalidOperation):
        return jsonify(error="piece and total_price must be numbers"), 400

    if "purchase_date" in data:
        purchase.purchase_date = _parse_date(data["purchase_date"], purchase.purchase_date)

    if "on_credit" in data:
        new_credit = bool(data["on_credit"])
        if purchase.status == "approved" and new_credit != purchase.on_credit:
            if new_credit:
                _apply_debt(purchase, wholesaler, g.current_user.id)
            else:
                # Remove debt
                amount = Decimal(purchase.total_price)
                wholesaler.debt_khata -= amount
                db.session.add(KhataTransaction(
                    wholesaler_id=wholesaler.id,
                    khata_type="debt",
                    entry_type="deduct",
                    amount=amount,
                    balance_after=wholesaler.debt_khata,
                    note=f"Removed credit for Purchase #{purchase.id}",
                    created_by=g.current_user.id
                ))
        purchase.on_credit = new_credit

    if "notes" in data:
        purchase.notes = (data["notes"] or "").strip() or None

    db.session.commit()
    return jsonify(purchase=purchase.to_dict())


@purchases_bp.delete("/<int:purchase_id>")
@role_required("admin")
def delete_purchase(purchase_id):
    purchase = db.session.get(Purchase, purchase_id)
    if not purchase:
        return jsonify(error="Purchase not found"), 404

    if purchase.status == "approved" and purchase.on_credit:
        wholesaler = purchase.wholesaler
        amount = Decimal(purchase.total_price)
        wholesaler.debt_khata -= amount
        db.session.add(KhataTransaction(
            wholesaler_id=wholesaler.id,
            khata_type="debt",
            entry_type="deduct",
            amount=amount,
            balance_after=wholesaler.debt_khata,
            note=f"Deleted Purchase #{purchase.id}",
            created_by=g.current_user.id
        ))

    db.session.delete(purchase)
    db.session.commit()
    return jsonify(status="Purchase deleted successfully")

