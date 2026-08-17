"""Startup DB seeding — creates the default admin account if no users exist."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging_config import logger
from app.core.security import hash_password
from app.models.iam import User, UserRole


async def seed_defaults(db: AsyncSession) -> None:
    existing = (await db.execute(select(User).limit(1))).scalar_one_or_none()
    if existing:
        logger.info("SEED | users already present — skipping")
        return

    admin = User(
        email="admin@portflow.ai",
        full_name="PortFlow Admin",
        hashed_password=hash_password("Admin1234!"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    manager = User(
        email="manager@portflow.ai",
        full_name="Port Manager",
        hashed_password=hash_password("Admin1234!"),
        role=UserRole.PORT_MANAGER,
        is_active=True,
        is_verified=True,
    )
    operator = User(
        email="operator@portflow.ai",
        full_name="Port Operator",
        hashed_password=hash_password("Admin1234!"),
        role=UserRole.OPERATIONS,
        is_active=True,
        is_verified=True,
    )
    db.add_all([admin, manager, operator])
    await db.commit()
    logger.info("SEED | default users created  →  admin@portflow.ai / manager@portflow.ai / operator@portflow.ai (Admin1234!)")
