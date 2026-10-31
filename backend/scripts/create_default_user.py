#!/usr/bin/env python3
"""Create the first platform admin of a production database (no seeded logins there).

Reads ADMIN_EMAIL, ADMIN_PASSWORD (at least 12 characters) and optional ADMIN_NAME from
the environment; never prints the password. Idempotent: an existing account is left as is.

    docker compose ... run --rm -e ADMIN_EMAIL=you@example.org -e ADMIN_PASSWORD \\
        backend python scripts/create_default_user.py
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from app.core.database import engine
from app.crud.user import user_crud
from app.schemas.auth import UserCreate


def main() -> int:
    email = os.environ.get("ADMIN_EMAIL", "")
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or len(password) < 12:
        print("Set ADMIN_EMAIL and ADMIN_PASSWORD (at least 12 characters)", file=sys.stderr)
        return 1
    with Session(engine) as db:
        if user_crud.get_by_email(db, email=email):
            print(f"{email} already exists; unchanged")
            return 0
        user = user_crud.create(
            db,
            obj_in=UserCreate(
                email=email,
                password=password,
                name=os.environ.get("ADMIN_NAME", "Platform Admin"),
                role="admin",
                is_active=True,
            ),
        )
    print(f"Created platform admin {user.email} ({user.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
