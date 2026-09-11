import os

from flask import Flask, jsonify, render_template, current_app

from .config import Config
from .extensions import cors, db, jwt


def _seed_admin():
    """Create the first admin account if the users table is empty."""
    from .models import User

    if db.session.query(User).count() > 0:
        return
    admin = User(name="Administrator", username="amardeep", role="admin")
    admin.set_password(os.getenv("ADMIN_PASSWORD", "manish123"))
    db.session.add(admin)
    db.session.commit()
    current_app.logger.warning(
        "Seeded default admin -> username: amardeep, password: %s (change it!)",
        os.getenv("ADMIN_PASSWORD", "manish123"),
    )


def create_app(config_class=Config):
    app = Flask(__name__,
                template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'))
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    with app.app_context():
        from . import models  # noqa: F401  (register models before create_all)

        # db.create_all() is removed to prevent connection overhead in serverless
        # Run this once locally or via a migration script
        # _seed_admin()

    @app.route("/")
    @app.route("/api/index")
    def index():
        return render_template("index.html")

    @app.route("/api/health")
    def health():
        return jsonify(status="ok", app="amardeep-readymade")

    from .auth.routes import auth_bp
    from .notifications.routes import notifications_bp
    from .purchases.routes import purchases_bp
    from .sales.routes import sales_bp
    from .users.routes import users_bp
    from .wholesalers.routes import wholesalers_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(wholesalers_bp)
    app.register_blueprint(purchases_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(notifications_bp)

    return app
