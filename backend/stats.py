"""
Simple statistics module for tracking reconciliation usage.
Uses CountAPI.xyz for persistent storage (free, no config needed).
"""
import requests
from datetime import datetime
from typing import Dict, Any

# CountAPI endpoints - persistent across deploys
COUNTAPI_NAMESPACE = "conciliador-egara"
COUNTAPI_KEY_TOTAL = "total-reconciliations"
COUNTAPI_KEY_ROWS = "total-rows"

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
        print(f"Warning: CountAPI error: {e}")
    return 0

def _countapi_get(key: str) -> int:
    """Get current value from CountAPI"""
    try:
        url = f"https://api.countapi.xyz/get/{COUNTAPI_NAMESPACE}/{key}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json().get("value", 0)
    except Exception as e:
        print(f"Warning: CountAPI error: {e}")
    return 0

def _countapi_create(key: str, initial_value: int = 0) -> bool:
    """Create a CountAPI key if it doesn't exist"""
    try:
        url = f"https://api.countapi.xyz/create?namespace={COUNTAPI_NAMESPACE}&key={key}&value={initial_value}&enable_reset=0"
        response = requests.get(url, timeout=5)
        return response.status_code == 200
    except:
        return False

def increment_reconciliation_count(rows_processed: int = 0) -> Dict[str, Any]:
    """Increment the reconciliation counter and update statistics"""
    # Increment total reconciliations
    total = _countapi_hit(COUNTAPI_KEY_TOTAL)

    # Increment total rows processed
    if rows_processed > 0:
        total_rows = _countapi_hit(COUNTAPI_KEY_ROWS, rows_processed)
    else:
        total_rows = _countapi_get(COUNTAPI_KEY_ROWS)

    return {
        "total_reconciliations": total,
        "total_rows_processed": total_rows,
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
    print("CountAPI counters initialized")