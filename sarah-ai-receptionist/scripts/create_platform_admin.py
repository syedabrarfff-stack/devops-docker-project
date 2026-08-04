#!/usr/bin/env python3
"""
Bootstraps the first platform_admin user directly against the database.

Every route that creates a user (admin.py's /clinics/onboard) is itself gated
behind require_admin, so there is no in-app way to create the very first
platform admin. Run this once against a fresh database.

Usage: python scripts/create_platform_admin.py --email you@aliyarsolutions.com --name "Syed Abrar"
(prompts for a password; or pass --password, not recommended for shell history)
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select  # noqa: E402
from app.core.database import get_db_context  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.user import User  # noqa: E402


async def main(email: str, full_name: str, password: str):
    async with get_db_context() as db:
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalar_one_or_none():
            print(f"A user with email {email} already exists — aborting.")
            return

        user = User(
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role="platform_admin",
        )
        db.add(user)

    print(f"Created platform_admin user: {email}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True, dest="full_name")
    parser.add_argument("--password", required=False, help="Omit to be prompted (recommended)")
    args = parser.parse_args()

    pw = args.password or getpass.getpass("Password for new platform admin: ")
    if len(pw) < 12:
        print("Password must be at least 12 characters.")
        sys.exit(1)

    asyncio.run(main(args.email, args.full_name, pw))
