"""
Simple statistics module for tracking reconciliation usage.
Uses CountAPI.xyz for persistent storage (free, no config needed).
Non-blocking: uses threading to avoid blocking the async event loop.
"""
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)

# CountAPI endpoints - persistent across deploys
COUNTAPI_NAMESPACE = "conciliador-egara"
COUNTAPI_KEY_TOTAL = "total-reconciliations"
COUNTAPI_KEY_ROWS = "total-rows"

# Thread pool for non-blocking HTTP calls
_executor = ThreadPoolExecutor(max_workers=2)

def _countapi_hit(key: str, amount: int = 1) -> int:
    """Increment a CountAPI counter and return new value"""
    try:
        if amount == 1:
            url = f"https://api.countapi.xyz/hit/{COUNTAPI_NAMESPACE}/{key}"
        else:
            url = f"https://api.countapi.xyz/update/{COUNTAPI_NAMESPACE}/{key}?amount={amount}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("value", 0)
    except Exception as e:
        logger.warning(f"CountAPI error: {e}")
    return 0

def _countapi_get(key: str) -> int:
    """Get current value from CountAPI"""
    try:
        url = f"https://api.countapi.xyz/get/{COUNTAPI_NAMESPACE}/{key}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("value", 0)
    except Exception as e:
        logger.warning(f"CountAPI error: {e}")
    return 0

def _countapi_create(key: str, initial_value: int = 0) -> bool:
    """Create a CountAPI key if it doesn't exist"""
    try:
        url = f"https://api.countapi.xyz/create?namespace={COUNTAPI_NAMESPACE}&key={key}&value={initial_value}&enable_reset=0"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

def _do_increment(rows_processed: int) -> None:
    """Perform the actual increment in a background thread (fire-and-forget)."""
    _countapi_hit(COUNTAPI_KEY_TOTAL)
    if rows_processed > 0:
        _countapi_hit(COUNTAPI_KEY_ROWS, rows_processed)

def increment_reconciliation_count(rows_processed: int = 0) -> Dict[str, Any]:
    """Increment stats in a background thread so we don't block the event loop."""
    _executor.submit(_do_increment, rows_processed)
    return {
        "total_reconciliations": 0,
        "total_rows_processed": 0,
        "last_reconciliation": datetime.now().isoformat()
    }

def get_stats() -> Dict[str, Any]:
    """Get current statistics"""
    total = _countapi_get(COUNTAPI_KEY_TOTAL)
    total_rows = _countapi_get(COUNTAPI_KEY_ROWS)

    return {
        "total_reconciliations": total,
        "total_rows_processed": total_rows
    }

def initialize_counters():
    """Initialize CountAPI counters (run once)"""
    _countapi_create(COUNTAPI_KEY_TOTAL, 0)
    _countapi_create(COUNTAPI_KEY_ROWS, 0)
    logger.info("CountAPI counters initialized")