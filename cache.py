"""Persistent cache for Oura data — preserves last known values between runs."""

import json
import os
from typing import Optional

CACHE_PATH = os.path.join(os.path.dirname(__file__), ".cache", "last_data.json")


def load() -> dict:
    """Load cached data from disk. Returns empty dict if no cache exists."""
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict) -> None:
    """Save data to disk cache."""
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


def merge_with_cache(fresh: dict) -> dict:
    """Merge freshly fetched data with the cache.

    For each section (sleep, readiness, activity, heart_rate, spo2):
    - If fresh data exists, use it and update the cache.
    - If fresh data is None/missing, fall back to the cached value.

    Returns the effective data to use and updates the cache file.
    """
    cached = load()
    effective = {}

    for section in ("sleep", "readiness", "activity", "heart_rate", "spo2"):
        fresh_val = fresh.get(section)
        if fresh_val:
            effective[section] = fresh_val
        else:
            effective[section] = cached.get(section)

    # Persist the effective state back so the cache always has the latest known values
    # Strip out the raw readings list to keep the cache file small
    to_save = {}
    for section, val in effective.items():
        if val and isinstance(val, dict):
            to_save[section] = {k: v for k, v in val.items() if k != "readings"}
        else:
            to_save[section] = val

    # Preserve heart rate readings separately if present (for chart regeneration on cache hits)
    if effective.get("heart_rate") and "readings" in effective["heart_rate"]:
        to_save["heart_rate"]["readings"] = effective["heart_rate"]["readings"]

    save(to_save)
    return effective
