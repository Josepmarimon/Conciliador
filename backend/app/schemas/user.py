"""Pydantic schemas for user management."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a new user (admin only)."""

    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters")
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserUpdate(BaseModel):
    """Schema for updating a user."""

    email: Optional[EmailStr] = None
    role: Optional[str] = Field(default=None, pattern="^(admin|user)$")
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    """Schema for user response."""

    id: UUID
    email: str
    role: str
    is_active: bool
    created_at: datetime
    tenant_id: UUID

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Schema for listing users."""

    users: list[UserResponse]
    total: int


class PasswordResetResponse(BaseModel):
    """Response after admin resets a user's password."""

    message: str
    temporary_password: str
