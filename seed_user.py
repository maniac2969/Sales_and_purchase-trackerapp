"""One-shot helper: create a new user.

Usage:
    python seed_user.py --name "Staff One" --username staff1 --password pass1234 [--role staff|admin]
"""
import argparse

from app import create_app
from app.extensions import db
from app.models import User

app = create_app()


def main():
    parser = argparse.ArgumentParser(description="Create a user")
    parser.add_argument("--name", required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--role", choices=["admin", "staff"], default="staff")
    args = parser.parse_args()

    with app.app_context():
        if User.query.filter_by(username=args.username).first():
            print(f"Username '{args.username}' already exists.")
            return
        user = User(name=args.name, username=args.username, role=args.role)
        user.set_password(args.password)
        db.session.add(user)
        db.session.commit()
        print(f"Created {args.role} user: {args.username}")


if __name__ == "__main__":
    main()
