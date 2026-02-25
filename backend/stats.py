"""
Simple statistics module for tracking reconciliation usage.
Uses in-memory counters (no external dependencies).
"""
from datetime import datetime
from typing import Dict, Any

_total_reconciliations = 0
_total_rows_processed = 0
_last_reconciliation: str | None = None


def increment_reconciliation_count(rows_processed: int = 0) -> Dict[str, Any]:
    """Increment in-memory stats counters."""
    global _total_reconciliations, _total_rows_processed, _last_reconciliation
    _total_reconciliations += 1
    _total_rows_processed += rows_processed
    _last_reconciliation = datetime.now().isoformat()
    return {
        "total_reconciliations": _total_reconciliations,
        "total_rows_processed": _total_rows_processed,
        "last_reconciliation": _last_reconciliation,
    }


def get_stats() -> Dict[str, Any]:
    """Get current in-memory statistics."""
    return {
        "total_reconciliations": _total_reconciliations,
        "total_rows_processed": _total_rows_processed,
    }
