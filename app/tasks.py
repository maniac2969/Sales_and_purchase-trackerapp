"""Celery tasks for regular (scheduled) notifications.

Run a worker + beat scheduler with:
    celery -A celery_worker.celery worker --beat --loglevel=info
"""
from datetime import date, timedelta

from sqlalchemy import func

from .decorators import notify_admins
from .extensions import celery, db
from .models import Purchase, Sale


@celery.task(name="app.tasks.daily_sales_summary")
def daily_sales_summary():
    """Scheduled every day (08:00 Asia/Karachi).

    Notifies admins with the previous day's approved sales total.
    """
    yesterday = date.today() - timedelta(days=1)
    row = (
        db.session.query(
            func.coalesce(func.sum(Sale.total_price), 0),
            func.coalesce(func.sum(Sale.piece), 0),
            func.count(Sale.id),
        )
        .filter(Sale.sale_date == yesterday, Sale.status == "approved")
        .first()
    )
    notify_admins(
        f"Daily sale summary for {yesterday.isoformat()}",
        f"{row[2]} sale(s), {row[1]} piece(s), total Rs. {float(row[0]):,.2f}",
    )


@celery.task(name="app.tasks.pending_approval_reminder")
def pending_approval_reminder():
    """Scheduled every day (09:00 Asia/Karachi).

    Reminds admins about sales/purchases waiting for approval.
    """
    pending_sales = Sale.query.filter_by(status="pending").count()
    pending_purchases = Purchase.query.filter_by(status="pending").count()
    if pending_sales or pending_purchases:
        notify_admins(
            "Pending approvals reminder",
            f"{pending_sales} sale(s) and {pending_purchases} purchase(s) "
            "are waiting for your approval.",
        )


@celery.task(name="app.tasks.monthly_sales_report")
def monthly_sales_report():
    """Scheduled on the 1st of every month (08:30 Asia/Karachi).

    Sends admins the completed month's totals.
    """
    today = date.today()
    last_month = today.replace(day=1) - timedelta(days=1)
    year, mon = last_month.year, last_month.month
    from sqlalchemy import extract

    row = (
        db.session.query(
            func.coalesce(func.sum(Sale.total_price), 0),
            func.coalesce(func.sum(Sale.piece), 0),
            func.count(Sale.id),
        )
        .filter(
            Sale.status == "approved",
            extract("year", Sale.sale_date) == year,
            extract("month", Sale.sale_date) == mon,
        )
        .first()
    )
    notify_admins(
        f"Monthly sale report for {year}-{mon:02d}",
        f"{row[2]} sale(s), {row[1]} piece(s), total Rs. {float(row[0]):,.2f}",
    )
