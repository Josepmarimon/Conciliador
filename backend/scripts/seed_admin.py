#!/usr/bin/env python3
"""
Seed script: creates a default admin user if no users exist.
Runs as part of the build/deploy process. Safe to run multiple times.

Default credentials:
    Email: admin@egara.com
    Password: Conciliador2025!
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.password import hash_password
from app.config import settings
from app.database import Base
from app.models.tenant import Tenant
from app.models.user import User, UserRole


async def seed():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Check if any users exist — skip if so
        result = await session.execute(select(func.count()).select_from(User))
        user_count = result.scalar()
        if user_count > 0:
            print(f"[seed] {user_count} user(s) already exist — skipping seed.")
            await engine.dispose()
            return

        # Create default tenant
        tenant = Tenant(name="Assessoria Egara")
        session.add(tenant)
        await session.flush()

        # Create admin user
        admin = User(
            email="admin@egara.com",
            hashed_password=hash_password("Conciliador2025!"),
            role=UserRole.ADMIN.value,
            tenant_id=tenant.id,
        )
        session.add(admin)
        await session.commit()

        print(f"[seed] Admin user created: admin@egara.com")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
