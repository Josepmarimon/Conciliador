"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request schema for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Response schema for successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshTokenRequest(BaseModel):
    """Request schema for token refresh."""

    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Request schema for password change."""

    current_password: str
    new_password: str


class UserInfo(BaseModel):
    """Basic user info included in token response."""

    id: str
    email: str
    role: str
    tenant_id: str
    tenant_name: str


class LoginResponse(BaseModel):
    """Complete login response with user info."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo
