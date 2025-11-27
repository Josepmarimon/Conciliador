"""
Simple statistics module for tracking reconciliation usage
"""
import json
import os
from datetime import datetime
from typing import Dict, Any

STATS_FILE = "reconciliation_stats.json"

def load_stats() -> Dict[str, Any]:
    """Load statistics from JSON file"""
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return initialize_stats()
    return initialize_stats()

def initialize_stats() -> Dict[str, Any]:
    """Initialize empty statistics"""
    return {
        "total_reconciliations": 0,
        "total_files_processed": 0,
        "total_rows_processed": 0,
        "last_reconciliation": None,
        "first_reconciliation": None,
        "daily_stats": {}
    }

def save_stats(stats: Dict[str, Any]) -> None:
    """Save statistics to JSON file"""
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2, default=str)
    except Exception as e:
        print(f"Warning: Could not save stats: {e}")

def increment_reconciliation_count(rows_processed: int = 0) -> Dict[str, Any]:
    """Increment the reconciliation counter and update statistics"""
    stats = load_stats()

    # Update counters
    stats["total_reconciliations"] += 1
    stats["total_files_processed"] += 1
    stats["total_rows_processed"] += rows_processed

    # Update timestamps
    now = datetime.now().isoformat()
    stats["last_reconciliation"] = now
    if stats["first_reconciliation"] is None:
        stats["first_reconciliation"] = now

    # Update daily stats
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in stats["daily_stats"]:
        stats["daily_stats"][today] = {"count": 0, "rows": 0}
    stats["daily_stats"][today]["count"] += 1
    stats["daily_stats"][today]["rows"] += rows_processed

    # Keep only last 30 days of daily stats
    if len(stats["daily_stats"]) > 30:
        dates = sorted(stats["daily_stats"].keys())
        for old_date in dates[:-30]:
            del stats["daily_stats"][old_date]

    save_stats(stats)
    return stats

def get_stats() -> Dict[str, Any]:
    """Get current statistics"""
    return load_stats()