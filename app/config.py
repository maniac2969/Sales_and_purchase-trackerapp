import os

from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")

    db_url = os.getenv("SUPABASE_DB_URL", "").strip()
    if db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///amardeep.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL = REDIS_URL
    CELERY_RESULT_BACKEND = REDIS_URL
    CELERY_TIMEZONE = "Asia/Karachi"
    CELERY_BEAT_SCHEDULE = {
        "daily-sales-summary": {
            "task": "app.tasks.daily_sales_summary",
            "schedule": crontab(hour=8, minute=0),
        },
        "pending-approval-reminder": {
            "task": "app.tasks.pending_approval_reminder",
            "schedule": crontab(hour=9, minute=0),
        },
        "monthly-sales-report": {
            "task": "app.tasks.monthly_sales_report",
            "schedule": crontab(hour=8, minute=30, day_of_month=1),
        },
    }
