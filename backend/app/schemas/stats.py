"""Pydantic schemas for reconciliation statistics."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ReconciliationLogResponse(BaseModel):
    id: UUID
    filename: str
    company_name: Optional[str]
    period: Optional[str]
    rows_processed: int
    matched_count: int
    pending_count: int
    unassigned_count: int
    created_at: datetime

    class Config:
        from_attributes = True


class UserStatsResponse(BaseModel):
    total_reconciliations: int
    total_rows_processed: int
    recent: list[ReconciliationLogResponse]


class AdminStatsEntry(ReconciliationLogResponse):
    user_email: str
