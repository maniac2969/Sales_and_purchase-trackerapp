"""Celery worker entrypoint.

Start worker + beat scheduler:
    celery -A celery_worker.celery worker --beat --loglevel=info
"""
from app import create_app
from app.extensions import celery  # noqa: F401  (exposed for `celery -A celery_worker`)

create_app()
