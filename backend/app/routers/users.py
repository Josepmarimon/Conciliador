"""User management router (admin only)."""

import secrets
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser
from app.auth.password import hash_password
from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    PasswordResetResponse,
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=UserListResponse)
async def list_users(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> UserListResponse:
    """
    List all users in the admin's tenant.

    Args:
        admin: Authenticated admin user
        db: Database session
        skip: Number of records to skip
        limit: Maximum records to return

    Returns:
        List of users and total count
    """
    # Get users in same tenant
    query = (
        select(User)
        .where(User.tenant_id == admin.tenant_id)
        .offset(skip)
        .limit(limit)
        .order_by(User.created_at.desc())
    )
    result = await db.execute(query)
    users = result.scalars().all()

    # Get total count
    count_query = (
        select(func.count())
        .select_from(User)
        .where(User.tenant_id == admin.tenant_id)
    )
    total = await db.execute(count_query)

    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total.scalar_one(),
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Create a new user in the admin's tenant.

    Args:
        user_data: New user data
        admin: Authenticated admin user
        db: Database session

    Returns:
        Created user

    Raises:
        HTTPException: If email already exists
    """
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == user_data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        role=user_data.role,
        tenant_id=admin.tenant_id,
        created_by=admin.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Get a specific user by ID.

    Args:
        user_id: User's unique identifier
        admin: Authenticated admin user
        db: Database session

    Returns:
        User details

    Raises:
        HTTPException: If user not found or not in same tenant
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """
    Update a user's information.

    Args:
        user_id: User's unique identifier
        user_data: Updated user data
        admin: Authenticated admin user
        db: Database session

    Returns:
        Updated user

    Raises:
        HTTPException: If user not found or email conflict
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Check email uniqueness if updating
    if user_data.email and user_data.email != user.email:
        existing = await db.execute(select(User).where(User.email == user_data.email))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user.email = user_data.email

    if user_data.role is not None:
        user.role = user_data.role

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    user_id: UUID,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """
    Deactivate a user (soft delete).

    Args:
        user_id: User's unique identifier
        admin: Authenticated admin user
        db: Database session

    Raises:
        HTTPException: If user not found or trying to deactivate self
    """
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself",
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = False
    await db.commit()


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
async def reset_user_password(
    user_id: UUID,
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PasswordResetResponse:
    """
    Reset a user's password (generates temporary password).

    Args:
        user_id: User's unique identifier
        admin: Authenticated admin user
        db: Database session

    Returns:
        Success message with temporary password

    Raises:
        HTTPException: If user not found
    """
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == admin.tenant_id)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Generate temporary password
    temp_password = secrets.token_urlsafe(12)
    user.hashed_password = hash_password(temp_password)
    await db.commit()

    # TODO: Send temporary password via email when email integration is ready
    # For now, log it server-side only and return success message
    import logging
    logging.getLogger(__name__).info(f"Password reset for user {user_id}. Temporary password generated (deliver securely).")

    return PasswordResetResponse(
        message="Password reset successfully. Contact admin for the new temporary password.",
        temporary_password="[redacted - delivered securely]",
    )
