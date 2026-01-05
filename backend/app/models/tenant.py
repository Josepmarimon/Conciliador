"""Tenant model for multi-tenancy support."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Tenant(Base):
    """
    Tenant model representing an organization/company.

    Each tenant has its own set of users and reconciliations.
    This enables multi-tenancy for the SaaS platform.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
    )

    # Relationships
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="tenant",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tenant {self.name}>"
