from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, g, jsonify, request
from sqlalchemy import extract, func

from ..decorators import notify_admins, role_required
from ..extensions import db
from ..models import Sale

sales_bp = Blueprint("sales", __name__, url_prefix="/api/sales")


def _parse_date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return default


@sales_bp.get("")
@role_required("admin", "staff")
def list_sales():
    """All sale entries for a specific day (default: today)."""
    target = _parse_date(request.args.get("date"), date.today())
    sales = Sale.query.filter_by(sale_date=target).order_by(Sale.id.asc()).all()
    approved = [s for s in sales if s.status == "approved"]
    return jsonify(
        date=target.isoformat(),
        sales=[s.to_dict() for s in sales],
        totals={
            "count": len(approved),
            "pieces": sum(s.piece for s in approved),
            "amount": float(sum(s.total_price or Decimal(0) for s in approved)),
        },
    )


@sales_bp.get("/monthly")
@role_required("admin", "staff")
def monthly_sales():
    """Monthly totals + per-item breakdown (approved sales only)."""
    month = request.args.get("month") or date.today().strftime("%Y-%m")
    try:
        year, mon = month.split("-")
        year, mon = int(year), int(mon)
        if not (1 <= mon <= 12):
            raise ValueError
    except Exception:
        return jsonify(error="month must be in YYYY-MM format"), 400

    filters = [
        Sale.status == "approved",
        extract("year", Sale.sale_date) == year,
        extract("month", Sale.sale_date) == mon,
    ]
    row = (
        db.session.query(
            func.coalesce(func.sum(Sale.total_price), 0),
            func.coalesce(func.sum(Sale.piece), 0),
            func.count(Sale.id),
        )
        .filter(*filters)
        .first()
    )
    by_item = (
        db.session.query(
            Sale.item,
            func.sum(Sale.piece),
            func.sum(Sale.total_price),
            func.count(Sale.id),
        )
        .filter(*filters)
        .group_by(Sale.item)
        .order_by(func.sum(Sale.total_price).desc())
        .all()
    )
    return jsonify(
        month=month,
        totals={
            "amount": float(row[0]),
            "pieces": int(row[1]),
            "count": int(row[2]),
        },
        by_item=[
            {"item": i, "pieces": int(p), "amount": float(a), "count": int(c)}
            for i, p, a, c in by_item
        ],
    )


@sales_bp.post("")
@role_required("admin", "staff")
def create_sale():
    data = request.get_json(force=True) or {}
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
    sale = Sale(
        item=item,
        piece=piece,
        total_price=total_price,
        sale_date=_parse_date(data.get("sale_date"), date.today()),
        notes=(data.get("notes") or "").strip() or None,
        created_by=g.current_user.id,
        status="pending" if is_staff else "approved",
    )
    db.session.add(sale)
    db.session.commit()

    if is_staff:
        notify_admins(
            "New sale awaiting approval",
            f"{g.current_user.name} added: {item} x {piece} = Rs. {total_price}",
        )
    return jsonify(sale=sale.to_dict()), 201


@sales_bp.get("/pending")
@role_required("admin")
def pending_sales():
    sales = Sale.query.filter_by(status="pending").order_by(Sale.created_at.asc()).all()
    return jsonify(sales=[s.to_dict() for s in sales])


@sales_bp.post("/<int:sale_id>/approve")
@role_required("admin")
def approve_sale(sale_id):
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify(error="Sale not found"), 404
    sale.status = "approved"
    db.session.commit()
    return jsonify(sale=sale.to_dict())


@sales_bp.post("/<int:sale_id>/reject")
@role_required("admin")
def reject_sale(sale_id):
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify(error="Sale not found"), 404
    sale.status = "rejected"
    db.session.commit()
    return jsonify(sale=sale.to_dict())


@sales_bp.put("/<int:sale_id>")
@role_required("admin")
def update_sale(sale_id):
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify(error="Sale not found"), 404

    data = request.get_json(force=True) or {}
    item = (data.get("item") or "").strip()
    if item:
        sale.item = item

    try:
        if "piece" in data:
            piece = int(data["piece"])
            if piece > 0:
                sale.piece = piece
        if "total_price" in data:
            sale.total_price = Decimal(str(data["total_price"]))
    except (TypeError, ValueError, InvalidOperation):
        return jsonify(error="piece and total_price must be numbers"), 400

    if "sale_date" in data:
        sale.sale_date = _parse_date(data["sale_date"], sale.sale_date)

    if "notes" in data:
        sale.notes = (data["notes"] or "").strip() or None

    db.session.commit()
    return jsonify(sale=sale.to_dict())


@sales_bp.delete("/<int:sale_id>")
@role_required("admin")
def delete_sale(sale_id):
    sale = db.session.get(Sale, sale_id)
    if not sale:
        return jsonify(error="Sale not found"), 404
    db.session.delete(sale)
    db.session.commit()
    return jsonify(status="Sale deleted successfully")

