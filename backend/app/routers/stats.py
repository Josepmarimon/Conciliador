"""Stats router for per-user reconciliation history."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import AdminUser, CurrentUser
from app.database import get_db
from app.models.reconciliation_log import ReconciliationLog
from app.models.user import User
from app.schemas.stats import AdminStatsEntry, UserStatsResponse

router = APIRouter(prefix="/stats", tags=["Statistics"])


@router.get("/me", response_model=UserStatsResponse)
async def my_stats(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserStatsResponse:
    """Get reconciliation statistics for the current user."""
    # Total count and rows
    totals = await db.execute(
        select(
            func.count(ReconciliationLog.id),
            func.coalesce(func.sum(ReconciliationLog.rows_processed), 0),
        ).where(ReconciliationLog.user_id == current_user.id)
    )
    total_reconciliations, total_rows_processed = totals.one()

    # Recent 20 logs
    recent_result = await db.execute(
        select(ReconciliationLog)
        .where(ReconciliationLog.user_id == current_user.id)
        .order_by(ReconciliationLog.created_at.desc())
        .limit(20)
    )
    recent = recent_result.scalars().all()

    return UserStatsResponse(
        total_reconciliations=total_reconciliations,
        total_rows_processed=total_rows_processed,
        recent=recent,
    )


@router.get("/all", response_model=list[AdminStatsEntry])
async def all_stats(
    admin: AdminUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminStatsEntry]:
    """Get all reconciliation logs for the tenant (admin only)."""
    result = await db.execute(
        select(ReconciliationLog, User.email)
        .join(User, ReconciliationLog.user_id == User.id)
        .where(ReconciliationLog.tenant_id == admin.tenant_id)
        .order_by(ReconciliationLog.created_at.desc())
    )
    rows = result.all()

    entries = []
    for log, user_email in rows:
        entries.append(
            AdminStatsEntry(
                id=log.id,
                filename=log.filename,
                company_name=log.company_name,
                period=log.period,
                rows_processed=log.rows_processed,
                matched_count=log.matched_count,
                pending_count=log.pending_count,
                unassigned_count=log.unassigned_count,
                created_at=log.created_at,
                user_email=user_email,
            )
        )
    return entries
