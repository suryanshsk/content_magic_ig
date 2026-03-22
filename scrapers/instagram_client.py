"""
scrapers/instagram_client.py
Unified Instagram client. ALL other modules import ONLY from here.
Automatically falls back from Apify to RapidAPI on quota or any error.
"""

import time
from datetime import datetime
from config import CREATORS, SLEEP_BETWEEN_CREATORS

from scrapers.apify_scraper import (
    scrape_profile as _apify_profile,
    scrape_reels   as _apify_reels,
    ApifyQuotaError, ApifyError,
)
from scrapers.rapidapi_scraper import (
    scrape_profile as _rapid_profile,
    scrape_reels   as _rapid_reels,
    RapidAPIQuotaError, RapidAPIError,
)
from storage.quota_tracker import should_use_apify, should_use_rapidapi, get_status_string


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Client] {msg}")


def get_profile(username: str) -> dict | None:
    """
    Fetch Instagram profile. Tries Apify first, falls back to RapidAPI.
    Returns standardised profile dict or None if both fail.
    """
    # ── Try Apify first ──────────────────────────────────────────────────────
    if should_use_apify():
        try:
            return _apify_profile(username)
        except ApifyQuotaError as e:
            _log(f"Apify quota hit — switching to RapidAPI. ({e})")
        except ApifyError as e:
            _log(f"Apify error for @{username}: {e} — trying RapidAPI")
        except Exception as e:
            _log(f"Unexpected Apify error for @{username}: {e} — trying RapidAPI")
    else:
        _log("Apify quota exhausted — going straight to RapidAPI")

    # ── Fall back to RapidAPI ─────────────────────────────────────────────────
    if should_use_rapidapi():
        try:
            return _rapid_profile(username)
        except RapidAPIQuotaError as e:
            _log(f"RapidAPI quota also hit: {e} — skipping @{username}")
            return None
        except RapidAPIError as e:
            _log(f"RapidAPI error for @{username}: {e}")
            return None
        except Exception as e:
            _log(f"Unexpected RapidAPI error for @{username}: {e}")
            return None
    else:
        _log(f"Both APIs quota exhausted — skipping @{username}")
        return None


def get_reels(username: str, count: int = 12) -> list:
    """
    Fetch recent reels. Tries Apify first, falls back to RapidAPI.
    Returns list of standardised reel dicts (may be empty).
    """
    # ── Try Apify first ──────────────────────────────────────────────────────
    if should_use_apify():
        try:
            return _apify_reels(username, count)
        except ApifyQuotaError as e:
            _log(f"Apify quota hit — switching to RapidAPI. ({e})")
        except ApifyError as e:
            _log(f"Apify reels error for @{username}: {e} — trying RapidAPI")
        except Exception as e:
            _log(f"Unexpected Apify reels error for @{username}: {e} — trying RapidAPI")
    else:
        _log("Apify quota exhausted — going straight to RapidAPI")

    # ── Fall back to RapidAPI ─────────────────────────────────────────────────
    if should_use_rapidapi():
        try:
            return _rapid_reels(username, count)
        except RapidAPIQuotaError as e:
            _log(f"RapidAPI quota also hit: {e} — returning empty reels for @{username}")
            return []
        except RapidAPIError as e:
            _log(f"RapidAPI reels error for @{username}: {e}")
            return []
        except Exception as e:
            _log(f"Unexpected RapidAPI reels error for @{username}: {e}")
            return []
    else:
        _log(f"Both APIs quota exhausted — returning empty reels for @{username}")
        return []


def get_full_creator_data(username: str, count: int = 12) -> dict | None:
    """
    Fetch both profile and reels for one creator.
    Returns combined dict or None if profile fetch fails.
    """
    profile = get_profile(username)
    if profile is None:
        _log(f"Profile fetch failed for @{username} — skipping")
        return None

    reels = get_reels(username, count)
    api_used = "apify" if should_use_apify() else "rapidapi"

    return {
        "profile":    profile,
        "reels":      reels,
        "scraped_at": datetime.utcnow().isoformat(),
        "api_used":   api_used,
    }


def scrape_all_creators(creators: list = None, count: int = 12) -> list:
    """
    Scrape all 73 creators. Prints progress and quota status every 10.
    Returns list of successful result dicts.
    """
    if creators is None:
        creators = CREATORS

    results = []
    total = len(creators)

    _log(f"Starting scrape of {total} creators...")
    _log(get_status_string())

    for i, creator in enumerate(creators, 1):
        username = creator["instagram"]
        name     = creator["name"]
        _log(f"[{i}/{total}] @{username} ({name})")

        data = get_full_creator_data(username, count)
        if data is not None:
            data["creator_name"] = name
            results.append(data)
            profile = data["profile"]
            reels   = data["reels"]
            _log(
                f"  ✅ {profile['followersCount']:,} followers | "
                f"{len(reels)} reels fetched"
            )
        else:
            _log(f"  ⚠️  Skipped @{username}")

        # Show quota status every 10 creators
        if i % 10 == 0:
            _log(get_status_string())

        # Rate limit sleep between creators
        if i < total:
            time.sleep(SLEEP_BETWEEN_CREATORS)

    _log(f"Scrape complete: {len(results)}/{total} creators successful")
    _log(get_status_string())
    return results
