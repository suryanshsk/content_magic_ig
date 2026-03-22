"""
storage/quota_tracker.py
Tracks Apify and RapidAPI monthly/daily usage in quota_tracker.json.
Auto-resets on 1st of month. Prevents hitting hard limits.
"""

import json
import os
from datetime import datetime
from config import QUOTA_FILE, APIFY_MONTHLY_LIMIT, RAPIDAPI_MONTHLY_LIMIT


DEFAULT_QUOTA = {
    "apify": {
        "calls_today": 0,
        "calls_month": 0,
        "last_daily_reset": "",
        "last_monthly_reset": ""
    },
    "rapidapi": {
        "calls_today": 0,
        "calls_month": 0,
        "last_daily_reset": "",
        "last_monthly_reset": ""
    }
}


def load_quota() -> dict:
    if not os.path.exists(QUOTA_FILE):
        save_quota(DEFAULT_QUOTA.copy())
        return DEFAULT_QUOTA.copy()
    try:
        with open(QUOTA_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        save_quota(DEFAULT_QUOTA.copy())
        return DEFAULT_QUOTA.copy()


def save_quota(quota: dict) -> None:
    with open(QUOTA_FILE, "w") as f:
        json.dump(quota, f, indent=2)


def reset_if_needed(quota: dict) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    this_month = datetime.now().strftime("%Y-%m")
    for service in ("apify", "rapidapi"):
        if quota[service]["last_daily_reset"] != today:
            quota[service]["calls_today"] = 0
            quota[service]["last_daily_reset"] = today
        if quota[service]["last_monthly_reset"] != this_month:
            quota[service]["calls_month"] = 0
            quota[service]["last_monthly_reset"] = this_month
    return quota


def increment(service: str, count: int = 1) -> None:
    quota = load_quota()
    quota = reset_if_needed(quota)
    quota[service]["calls_today"] += count
    quota[service]["calls_month"] += count
    save_quota(quota)


def get_remaining(service: str) -> dict:
    quota = load_quota()
    quota = reset_if_needed(quota)
    limit = APIFY_MONTHLY_LIMIT if service == "apify" else RAPIDAPI_MONTHLY_LIMIT
    used = quota[service]["calls_month"]
    return {
        "used_month":  used,
        "limit_month": limit,
        "remaining":   max(0, limit - used),
        "ok":          used < limit
    }


def should_use_apify() -> bool:
    return get_remaining("apify")["ok"]


def should_use_rapidapi() -> bool:
    return get_remaining("rapidapi")["ok"]


def get_status_string() -> str:
    a = get_remaining("apify")
    r = get_remaining("rapidapi")
    return (
        f"Apify: {a['used_month']}/{a['limit_month']} this month | "
        f"RapidAPI: {r['used_month']}/{r['limit_month']} this month"
    )
