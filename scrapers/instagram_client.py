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


def _get_profile_with_source(username: str) -> tuple[dict | None, str, str]:
    """
    Fetch Instagram profile. Tries Apify first, then RapidAPI, then InstaTouch fallback.
    Returns standardised profile dict or None if both fail.
    """
    if SCRAPER_MODE == "rapidapi_only":
        _log("RapidAPI-only mode active — skipping Apify")
    # ── Try Apify first ──────────────────────────────────────────────────────
    elif should_use_apify():
        try:
            return _apify_profile(username), "apify", ""
        except ApifyQuotaError as e:
            last_error = f"Apify quota: {e}"
            _log(f"Apify quota hit — switching to RapidAPI. ({e})")
        except ApifyError as e:
            last_error = f"Apify error: {e}"
            _log(f"Apify error for @{username}: {e} — trying RapidAPI")
        except Exception as e:
            last_error = f"Apify unexpected error: {e}"
            _log(f"Unexpected Apify error for @{username}: {e} — trying RapidAPI")
    else:
        last_error = "Apify quota exhausted"
        _log("Apify quota exhausted — going straight to RapidAPI")

    # ── Fall back to RapidAPI ─────────────────────────────────────────────────
    if should_use_rapidapi():
        try:
            return _rapid_profile(username), "rapidapi", ""
        except RapidAPIQuotaError as e:
            last_error = f"RapidAPI quota: {e}"
            _log(f"RapidAPI quota also hit: {e} — trying InstaTouch fallback")
        except RapidAPIError as e:
            last_error = f"RapidAPI error: {e}"
            _log(f"RapidAPI error for @{username}: {e} — trying InstaTouch fallback")
        except Exception as e:
            last_error = f"RapidAPI unexpected error: {e}"
            _log(f"Unexpected RapidAPI error for @{username}: {e} — trying InstaTouch fallback")
    else:
        last_error = "RapidAPI quota exhausted"
        _log(f"Both APIs quota exhausted — trying InstaTouch fallback for @{username}")

    # ── Final fallback: InstaTouch ────────────────────────────────────────────
    if _can_use_instatouch():
        try:
            return _instatouch_profile(username), "instatouch", ""
        except InstaTouchRateLimitError as e:
            _log(f"InstaTouch rate limited for @{username}: {e}")
            return None, "none", f"InstaTouch rate limit: {e}"
        except InstaTouchError as e:
            _log(f"InstaTouch error for @{username}: {e}")
            return None, "none", f"InstaTouch error: {e}"
        except Exception as e:
            _log(f"Unexpected InstaTouch error for @{username}: {e}")
            return None, "none", f"InstaTouch unexpected error: {e}"

    _log(f"InstaTouch fallback disabled/missing session — skipping @{username}")
    return None, "none", last_error if 'last_error' in locals() else "No provider succeeded"


def get_profile(username: str) -> dict | None:
    profile, _, _ = _get_profile_with_source(username)
    return profile


def _get_reels_with_source(username: str, count: int = 12) -> tuple[list, str, str]:
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
                return apify_reels, "apify", ""
            _log(f"Apify returned 0 reels for @{username} — trying RapidAPI fallback")
        except ApifyQuotaError as e:
            last_error = f"Apify quota: {e}"
            _log(f"Apify quota hit — switching to RapidAPI. ({e})")
        except ApifyError as e:
            last_error = f"Apify error: {e}"
            _log(f"Apify reels error for @{username}: {e} — trying RapidAPI")
        except Exception as e:
            last_error = f"Apify unexpected error: {e}"
            _log(f"Unexpected Apify reels error for @{username}: {e} — trying RapidAPI")
    else:
        last_error = "Apify quota exhausted"
        _log("Apify quota exhausted — going straight to RapidAPI")

    # ── Fall back to RapidAPI ─────────────────────────────────────────────────
    if should_use_rapidapi():
        try:
            rapid_reels = _rapid_reels(username, count)
            if rapid_reels:
                return rapid_reels, "rapidapi", ""
            _log(f"RapidAPI returned 0 reels for @{username} — trying InstaTouch fallback")
        except RapidAPIQuotaError as e:
            last_error = f"RapidAPI quota: {e}"
            _log(f"RapidAPI quota also hit: {e} — trying InstaTouch fallback")
        except RapidAPIError as e:
            last_error = f"RapidAPI error: {e}"
            _log(f"RapidAPI reels error for @{username}: {e} — trying InstaTouch fallback")
        except Exception as e:
            last_error = f"RapidAPI unexpected error: {e}"
            _log(f"Unexpected RapidAPI reels error for @{username}: {e} — trying InstaTouch fallback")
    else:
        last_error = "RapidAPI quota exhausted"
        _log(f"Both APIs quota exhausted — trying InstaTouch fallback for @{username}")

    # ── Final fallback: InstaTouch ────────────────────────────────────────────
    if _can_use_instatouch():
        try:
            return _instatouch_reels(username, count), "instatouch", ""
        except InstaTouchRateLimitError as e:
            _log(f"InstaTouch rate limited for @{username}: {e}")
            return [], "none", f"InstaTouch rate limit: {e}"
        except InstaTouchError as e:
            _log(f"InstaTouch error for @{username}: {e}")
            return [], "none", f"InstaTouch error: {e}"
        except Exception as e:
            _log(f"Unexpected InstaTouch reels error for @{username}: {e}")
            return [], "none", f"InstaTouch unexpected error: {e}"

    _log(f"InstaTouch fallback disabled/missing session — returning empty reels for @{username}")
    return [], "none", last_error if 'last_error' in locals() else "No provider succeeded"


def get_reels(username: str, count: int = 12) -> list:
    reels, _, _ = _get_reels_with_source(username, count)
    return reels


def get_full_creator_data(username: str, count: int = 12) -> dict | None:
    """
    Fetch both profile and reels for one creator.
    Returns combined dict or None if profile fetch fails.
    """
    profile, profile_source, profile_error = _get_profile_with_source(username)
    if profile is None:
        _log(f"Profile fetch failed for @{username} — skipping")
        return None

    reels, reels_source, reels_error = _get_reels_with_source(username, count)
    api_used = reels_source if reels_source != "none" else profile_source

    return {
        "profile":    profile,
        "reels":      reels,
        "scraped_at": datetime.utcnow().isoformat(),
        "api_used":   api_used,
        "profile_source": profile_source,
        "reels_source": reels_source,
        "profile_error": profile_error,
        "reels_error": reels_error,
        "fetch_status": "PARTIAL" if (not reels and reels_error) else "SUCCESS",
    }


def scrape_all_creators(creators: list = None, count: int = 12, include_failures: bool = False):
    """
    Scrape all 73 creators. Prints progress and quota status every 10.
    Returns list of successful result dicts.
    If include_failures=True, returns tuple (results, failures).
    """
    if creators is None:
        creators = CREATORS

    results = []
    failures = []
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
            failures.append({
                "creator_name": name,
                "username": username,
                "status": "FAILED",
                "api_used": "none",
                "profile_source": "none",
                "reels_source": "none",
                "reels_fetched": 0,
                "error": "Profile fetch failed on all providers",
            })

        # Show quota status every 10 creators
        if i % 10 == 0:
            _log(get_status_string())

        # Rate limit sleep between creators
        if i < total:
            time.sleep(SLEEP_BETWEEN_CREATORS)

    # Retry one pass for failed creators to improve coverage in noisy API windows.
    if failures:
        _log(f"Retrying failed creators once: {len(failures)}")
        retry_failures = []
        for item in failures:
            username = item["username"]
            name = item["creator_name"]
            data = get_full_creator_data(username, count)
            if data is not None:
                data["creator_name"] = name
                results.append(data)
                _log(f"  ✅ Retry recovered @{username}")
            else:
                retry_failures.append(item)
            time.sleep(max(1, SLEEP_BETWEEN_CREATORS // 2))
        failures = retry_failures

    _log(f"Scrape complete: {len(results)}/{total} creators successful")
    _log(get_status_string())
    if include_failures:
        return results, failures
    return results
