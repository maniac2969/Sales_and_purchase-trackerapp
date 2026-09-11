from celery import Celery
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()

celery = Celery("amardeep_readymade")


def init_celery(app):
    """Attach the Flask app to Celery so tasks run inside an app context."""
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
        beat_schedule=app.config["CELERY_BEAT_SCHEDULE"],
        timezone=app.config["CELERY_TIMEZONE"],
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )

    class FlaskTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = FlaskTask
    return celery
