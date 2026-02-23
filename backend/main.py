"""Conciliador FIFO API - Main application."""

import base64
import json
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.config import settings
from app.database import close_db, get_db
from app.models.reconciliation_log import ReconciliationLog
from app.routers import auth_router, stats_router, users_router
from reconciliation import process_excel
from stats import get_stats, increment_reconciliation_count


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown events."""
    # Startup
    yield
    # Shutdown
    await close_db()


app = FastAPI(
    title="Conciliador FIFO API",
    description="Accounting reconciliation tool for matching invoices with payments",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(stats_router)


@app.get("/")
def read_root():
    """Health check endpoint."""
    stats = get_stats()
    return {
        "message": "Conciliador FIFO API is running",
        "version": "2.0.0",
        "total_reconciliations": stats["total_reconciliations"],
    }


@app.get("/stats")
def get_statistics():
    """Get usage statistics (public endpoint)."""
    return get_stats()


@app.post("/conciliate")
async def conciliate_endpoint(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    tol: float = 0.01,
    ar_prefix: str = "43",
    ap_prefix: str = "40,41",
    justifications: Optional[str] = None,
    output_format: str = "human",
):
    """
    Process an Excel file for reconciliation.

    Requires authentication. The file is processed using the waterfall
    reconciliation algorithm and returns matched/unmatched transactions.

    Args:
        file: Excel file (.xlsx) with accounting data
        tol: Tolerance for amount matching (default: 0.01)
        ar_prefix: Account prefix for Accounts Receivable (default: "43")
        ap_prefix: Account prefix for Accounts Payable (default: "40")
        justifications: JSON string of user justifications for unmatched payments
        output_format: "human" (single tab) or "detailed" (multi-tab)
        current_user: Authenticated user (injected by dependency)

    Returns:
        Reconciliation results with summary, details, and downloadable Excel
    """
    if not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=400,
            detail="Invalid file format. Please upload an Excel file (.xlsx).",
        )

    try:
        contents = await file.read()

        # Parse justifications if provided
        justifications_dict = None
        if justifications:
            try:
                justifications_dict = json.loads(justifications)
            except json.JSONDecodeError:
                justifications_dict = None

        response_data, output_excel = process_excel(
            contents, tol, ar_prefix, ap_prefix, justifications_dict, output_format
        )

        # Count total rows processed
        total_rows = 0
        if "summary" in response_data:
            for item in response_data["summary"]:
                total_rows += item.get("Movimientos", 0)

        # Increment statistics
        increment_reconciliation_count(total_rows)

        # Count matched and pending from details
        details = response_data.get("details", {})
        matched_count = len(details.get("Clientes_Detalle", [])) + len(
            details.get("Proveedores_Detalle", [])
        )
        pending_count = len(details.get("Pendientes_Clientes", [])) + len(
            details.get("Pendientes_Proveedores", [])
        )
        unassigned_count = total_rows - matched_count - pending_count
        if unassigned_count < 0:
            unassigned_count = 0

        # Save reconciliation log
        log = ReconciliationLog(
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
            filename=file.filename,
            company_name=response_data.get("company_name"),
            period=response_data.get("period"),
            rows_processed=total_rows,
            matched_count=matched_count,
            pending_count=pending_count,
            unassigned_count=unassigned_count,
        )
        db.add(log)
        await db.commit()

        # Encode Excel file as base64
        b64_file = base64.b64encode(output_excel.getvalue()).decode()

        return {
            "summary": response_data["summary"],
            "meta": response_data["meta"],
            "details": response_data.get("details", {}),
            "company_name": response_data.get("company_name"),
            "period": response_data.get("period"),
            "filename": file.filename.replace(".xlsx", "_conciliado.xlsx"),
            "file_b64": b64_file,
            "user": current_user.email,  # Include user info in response
        }

    except Exception as e:
        import logging
        import traceback

        logging.getLogger(__name__).error(f"Reconciliation error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Error processing file. Please check the file format and try again.",
        )
