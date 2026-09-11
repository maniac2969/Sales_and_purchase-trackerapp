from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="staff")  # admin | staff
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sales = db.relationship("Sale", backref="user", lazy="dynamic")
    purchases = db.relationship("Purchase", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Sale(db.Model):
    """A shop sale entry. Staff-added sales are 'pending' until admin approves."""

    __tablename__ = "sales"

    id = db.Column(db.Integer, primary_key=True)
    item = db.Column(db.String(200), nullable=False)
    piece = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    sale_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(10), nullable=False, default="approved", index=True)
    notes = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "item": self.item,
            "piece": self.piece,
            "total_price": float(self.total_price),
            "sale_date": self.sale_date.isoformat() if self.sale_date else None,
            "status": self.status,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_by_name": self.user.name if self.user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Wholesaler(db.Model):
    """Supplier/wholesaler with two khata balances.

    debt_khata    -> what the shop owes the wholesaler (dain)
    uchanti_khata -> advance / uchaari the shop has given the wholesaler
    """

    __tablename__ = "wholesalers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    phone = db.Column(db.String(30))
    address = db.Column(db.String(300))
    debt_khata = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    uchanti_khata = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    khata_transactions = db.relationship(
        "KhataTransaction", backref="wholesaler", lazy="dynamic",
        cascade="all, delete-orphan",
    )
    purchases = db.relationship(
        "Purchase", backref="wholesaler", lazy="dynamic",
        cascade="all, delete-orphan",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "phone": self.phone,
            "address": self.address,
            "debt_khata": float(self.debt_khata),
            "uchanti_khata": float(self.uchanti_khata),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KhataTransaction(db.Model):
    """Every change made to a wholesaler's debt or uchanti khata."""

    __tablename__ = "khata_transactions"

    id = db.Column(db.Integer, primary_key=True)
    wholesaler_id = db.Column(
        db.Integer, db.ForeignKey("wholesalers.id"), nullable=False, index=True
    )
    khata_type = db.Column(db.String(10), nullable=False)  # debt | uchanti
    entry_type = db.Column(db.String(10), nullable=False)  # add | deduct
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    balance_after = db.Column(db.Numeric(12, 2), nullable=False)
    note = db.Column(db.String(300))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "khata_type": self.khata_type,
            "entry_type": self.entry_type,
            "amount": float(self.amount),
            "balance_after": float(self.balance_after),
            "note": self.note,
            "created_by_name": self.user.name if self.user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    user = db.relationship("User")


class Purchase(db.Model):
    """A shop purchase from a wholesaler. Staff-added purchases need approval."""

    __tablename__ = "purchases"

    id = db.Column(db.Integer, primary_key=True)
    wholesaler_id = db.Column(
        db.Integer, db.ForeignKey("wholesalers.id"), nullable=False, index=True
    )
    item = db.Column(db.String(200), nullable=False)
    piece = db.Column(db.Integer, nullable=False, default=1)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    purchase_date = db.Column(db.Date, nullable=False, index=True)
    on_credit = db.Column(db.Boolean, nullable=False, default=False)
    status = db.Column(db.String(10), nullable=False, default="approved", index=True)
    notes = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "wholesaler_id": self.wholesaler_id,
            "wholesaler_name": self.wholesaler.name if self.wholesaler else None,
            "item": self.item,
            "piece": self.piece,
            "total_price": float(self.total_price),
            "purchase_date": self.purchase_date.isoformat() if self.purchase_date else None,
            "on_credit": self.on_credit,
            "status": self.status,
            "notes": self.notes,
            "created_by": self.created_by,
            "created_by_name": self.user.name if self.user else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
