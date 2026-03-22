"""
scrapers/instagram_client.py
Unified Instagram client. ALL other modules import ONLY from here.
Automatically falls back from Apify to RapidAPI on quota or any error.
"""

import time
from datetime import datetime
from config import (
    CREATORS,
    SLEEP_BETWEEN_CREATORS,
    SCRAPER_MODE,
    ENABLE_INSTATOUCH_FALLBACK,
    INSTATOUCH_SESSION,
    AUTO_FETCH_INSTAGRAM_SESSION,
)

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
from scrapers.instatouch_scraper import (
    scrape_profile as _instatouch_profile,
    scrape_reels as _instatouch_reels,
    InstaTouchError,
    InstaTouchRateLimitError,
)
from storage.quota_tracker import should_use_apify, should_use_rapidapi, get_status_string


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Client] {msg}")


def _can_use_instatouch() -> bool:
    return ENABLE_INSTATOUCH_FALLBACK and (bool(INSTATOUCH_SESSION) or AUTO_FETCH_INSTAGRAM_SESSION)


def _get_profile_with_source(username: str) -> tuple[dict | None, str]:
    """
    Fetch Instagram profile. Tries Apify first, then RapidAPI, then InstaTouch fallback.
    Returns standardised profile dict or None if both fail.
    """
    if SCRAPER_MODE == "rapidapi_only":
        _log("RapidAPI-only mode active — skipping Apify")
    # ── Try Apify first ──────────────────────────────────────────────────────
    elif should_use_apify():
        try:
            return _apify_profile(username), "apify"
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
            return _rapid_profile(username), "rapidapi"
        except RapidAPIQuotaError as e:
            _log(f"RapidAPI quota also hit: {e} — trying InstaTouch fallback")
        except RapidAPIError as e:
            _log(f"RapidAPI error for @{username}: {e} — trying InstaTouch fallback")
        except Exception as e:
            _log(f"Unexpected RapidAPI error for @{username}: {e} — trying InstaTouch fallback")
    else:
        _log(f"Both APIs quota exhausted — trying InstaTouch fallback for @{username}")

    # ── Final fallback: InstaTouch ────────────────────────────────────────────
    if _can_use_instatouch():
        try:
            return _instatouch_profile(username), "instatouch"
        except InstaTouchRateLimitError as e:
            _log(f"InstaTouch rate limited for @{username}: {e}")
            return None, "none"
        except InstaTouchError as e:
            _log(f"InstaTouch error for @{username}: {e}")
            return None, "none"
        except Exception as e:
            _log(f"Unexpected InstaTouch error for @{username}: {e}")
            return None, "none"

    _log(f"InstaTouch fallback disabled/missing session — skipping @{username}")
    return None, "none"


def get_profile(username: str) -> dict | None:
    profile, _ = _get_profile_with_source(username)
    return profile


def _get_reels_with_source(username: str, count: int = 12) -> tuple[list, str]:
    """
    Fetch recent reels. Tries Apify first, then RapidAPI, then InstaTouch fallback.
    Returns list of standardised reel dicts (may be empty).
    """
    if SCRAPER_MODE == "rapidapi_only":
        _log("RapidAPI-only mode active — skipping Apify")
    # ── Try Apify first ──────────────────────────────────────────────────────
    elif should_use_apify():
        try:
            apify_reels = _apify_reels(username, count)
            if apify_reels:
                return apify_reels, "apify"
            _log(f"Apify returned 0 reels for @{username} — trying RapidAPI fallback")
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
            rapid_reels = _rapid_reels(username, count)
            if rapid_reels:
                return rapid_reels, "rapidapi"
            _log(f"RapidAPI returned 0 reels for @{username} — trying InstaTouch fallback")
        except RapidAPIQuotaError as e:
            _log(f"RapidAPI quota also hit: {e} — trying InstaTouch fallback")
        except RapidAPIError as e:
            _log(f"RapidAPI reels error for @{username}: {e} — trying InstaTouch fallback")
        except Exception as e:
            _log(f"Unexpected RapidAPI reels error for @{username}: {e} — trying InstaTouch fallback")
    else:
        _log(f"Both APIs quota exhausted — trying InstaTouch fallback for @{username}")

    # ── Final fallback: InstaTouch ────────────────────────────────────────────
    if _can_use_instatouch():
        try:
            return _instatouch_reels(username, count), "instatouch"
        except InstaTouchRateLimitError as e:
            _log(f"InstaTouch rate limited for @{username}: {e}")
            return [], "none"
        except InstaTouchError as e:
            _log(f"InstaTouch error for @{username}: {e}")
            return [], "none"
        except Exception as e:
            _log(f"Unexpected InstaTouch reels error for @{username}: {e}")
            return [], "none"

    _log(f"InstaTouch fallback disabled/missing session — returning empty reels for @{username}")
    return [], "none"


def get_reels(username: str, count: int = 12) -> list:
    reels, _ = _get_reels_with_source(username, count)
    return reels


def get_full_creator_data(username: str, count: int = 12) -> dict | None:
    """
    Fetch both profile and reels for one creator.
    Returns combined dict or None if profile fetch fails.
    """
    profile, profile_source = _get_profile_with_source(username)
    if profile is None:
        _log(f"Profile fetch failed for @{username} — skipping")
        return None

    reels, reels_source = _get_reels_with_source(username, count)
    api_used = reels_source if reels_source != "none" else profile_source

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
