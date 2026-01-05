#!/usr/bin/env python3
"""
Script to create the first admin user and tenant.

Usage:
    python scripts/create_admin.py --email admin@example.com --password securepass123 --tenant "My Company"

This script is meant to be run once to bootstrap the initial admin user.
Subsequent users should be created via the admin API.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth.password import hash_password
from app.config import settings
from app.database import Base
from app.models.tenant import Tenant
from app.models.user import User, UserRole


async def create_admin(
    email: str,
    password: str,
    tenant_name: str,
) -> None:
    """
    Create initial admin user and tenant.

    Args:
        email: Admin's email address
        password: Admin's password
        tenant_name: Name of the tenant/organization
    """
    # Create engine and session
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        # Create tables if they don't exist
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Check if user already exists
        result = await session.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(f"Error: User with email '{email}' already exists.")
            await engine.dispose()
            sys.exit(1)

        # Check if tenant already exists
        result = await session.execute(select(Tenant).where(Tenant.name == tenant_name))
        tenant = result.scalar_one_or_none()

        if not tenant:
            # Create tenant
            tenant = Tenant(name=tenant_name)
            session.add(tenant)
            await session.flush()  # Get the tenant ID
            print(f"Created tenant: {tenant_name} (ID: {tenant.id})")
        else:
            print(f"Using existing tenant: {tenant_name} (ID: {tenant.id})")

        # Create admin user
        admin = User(
            email=email,
            hashed_password=hash_password(password),
            role=UserRole.ADMIN.value,
            tenant_id=tenant.id,
        )
        session.add(admin)
        await session.commit()

        print(f"\nAdmin user created successfully!")
        print(f"  Email: {email}")
        print(f"  Role: admin")
        print(f"  Tenant: {tenant_name}")
        print(f"  User ID: {admin.id}")

    await engine.dispose()


def main():
    """Parse arguments and run admin creation."""
    parser = argparse.ArgumentParser(
        description="Create the first admin user for Conciliador",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/create_admin.py --email admin@egara.com --password MySecurePass123 --tenant "Assessoria Egara"

Note: Make sure to set DATABASE_URL in your .env file before running this script.
        """,
    )
    parser.add_argument(
        "--email",
        required=True,
        help="Admin's email address",
    )
    parser.add_argument(
        "--password",
        required=True,
        help="Admin's password (min 8 characters)",
    )
    parser.add_argument(
        "--tenant",
        required=True,
        help="Name of the organization/company",
    )

    args = parser.parse_args()

    # Validate password
    if len(args.password) < 8:
        print("Error: Password must be at least 8 characters long.")
        sys.exit(1)

    # Run async function
    asyncio.run(create_admin(args.email, args.password, args.tenant))


if __name__ == "__main__":
    main()
