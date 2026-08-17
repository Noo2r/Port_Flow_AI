#!/usr/bin/env python3
"""
One-off script: insert the two missing demo accounts into the running database.
================================================================================
seed_defaults() in app/db/seed.py is intentionally guarded by
"skip if ANY user already exists" so it never re-runs on a populated database.
The two demo users added in commit 8fa192a (manager@portflow.ai,
operator@portflow.ai) were therefore never written to the existing DB.

This script is the safe, one-time fix:
  - Idempotent: checks for the email before inserting — safe to run again.
  - Non-destructive: touches only the `users` table and only for these two emails.
  - Uses the same DB URL, hashing, and model layer as the rest of the backend.

Run inside the demo container (NOT the isolated test stack):
    docker exec portflow_api python scripts/add_demo_users.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone

sys.path.insert(0, "/app")

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.models.iam import Base, User, UserRole  # noqa: F401 (Base triggers mapper)

# ── Same credentials as the main app ──────────────────────────────────────────
DB_URL = "postgresql+asyncpg://portflow:portflow@db:5432/portflow"

DEMO_USERS = [
    {
        "email":     "manager@portflow.ai",
        "full_name": "Port Manager",
        "password":  "Admin1234!",
        "role":      UserRole.PORT_MANAGER,
    },
    {
        "email":     "operator@portflow.ai",
        "full_name": "Port Operator",
        "password":  "Admin1234!",
        "role":      UserRole.OPERATIONS,
    },
]


async def main() -> None:
    engine = create_async_engine(DB_URL, echo=False)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with AsyncSessionLocal() as db:
        created = []
        already_present = []

        for spec in DEMO_USERS:
            existing = (
                await db.execute(select(User).where(User.email == spec["email"]))
            ).scalar_one_or_none()

            if existing:
                already_present.append(spec["email"])
                continue

            user = User(
                email=spec["email"],
                full_name=spec["full_name"],
                hashed_password=hash_password(spec["password"]),
                role=spec["role"],
                is_active=True,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
            )
            db.add(user)
            created.append(spec["email"])

        await db.commit()

    # ── Summary ───────────────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  add_demo_users.py — result")
    print("=" * 60)
    if created:
        for email in created:
            print(f"  ✅  CREATED  {email}")
    if already_present:
        for email in already_present:
            print(f"  ℹ️   SKIPPED  {email}  (already exists)")
    if not created and not already_present:
        print("  (nothing to do)")
    print()

    # ── Final verification: list all users ───────────────────────────────────
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(select(User.email, User.role).order_by(User.id))).all()

    print("  Current users table (email + role):")
    print("  " + "-" * 48)
    for email, role in rows:
        role_str = role.value if hasattr(role, "value") else str(role)
        print(f"  {email:<35}  {role_str}")
    print("  " + "-" * 48)
    print()

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
