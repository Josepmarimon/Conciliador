"""JWT token creation and verification."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from uuid import UUID

from jose import JWTError, jwt

from app.config import settings


class TokenError(Exception):
    """Exception raised for token-related errors."""

    pass


def create_access_token(
    user_id: UUID,
    email: str,
    role: str,
    tenant_id: UUID,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User's unique identifier
        email: User's email address
        role: User's role (admin/user)
        tenant_id: User's tenant identifier
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    expire = datetime.utcnow() + expires_delta

    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "tenant_id": str(tenant_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User's unique identifier

    Returns:
        Encoded JWT refresh token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify and decode a JWT token.

    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")

    Returns:
        Decoded token payload

    Raises:
        TokenError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise TokenError(f"Invalid token type. Expected {token_type}")

        return payload

    except JWTError as e:
        raise TokenError(f"Invalid token: {str(e)}")


def get_user_id_from_token(token: str) -> UUID:
    """
    Extract user ID from a token.

    Args:
        token: JWT token string

    Returns:
        User's UUID

    Raises:
        TokenError: If token is invalid
    """
    payload = verify_token(token)
    return UUID(payload["sub"])
