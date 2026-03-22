"""
scrapers/apify_scraper.py
Primary Instagram scraper using Apify REST API (free tier: 100 runs/month).
Fetches profile info and last N reels for any Instagram username.
"""

import re
import time
import requests
from datetime import datetime, timezone
from config import APIFY_API_TOKEN, APIFY_ACTOR_ID, APIFY_MONTHLY_LIMIT
from storage.quota_tracker import increment, get_remaining


class ApifyQuotaError(Exception):
    pass


class ApifyError(Exception):
    pass


BASE = "https://api.apify.com/v2"


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Apify] {msg}")


def _run_actor(input_data: dict, timeout_secs: int = 180) -> str:
    """Start an actor run and return the run_id."""
    # Apify API expects owner~actor format in endpoint path.
    actor_id = APIFY_ACTOR_ID.replace("/", "~")
    url = f"{BASE}/acts/{actor_id}/runs"
    params = {"token": APIFY_API_TOKEN}
    r = requests.post(url, json=input_data, params=params, timeout=30)
    if r.status_code not in (200, 201):
        raise ApifyError(f"Failed to start actor: {r.status_code} {r.text[:200]}")
    return r.json()["data"]["id"]


def _wait_for_run(run_id: str, timeout_secs: int = 180) -> str:
    """Poll until run finishes. Returns defaultDatasetId."""
    url = f"{BASE}/actor-runs/{run_id}"
    params = {"token": APIFY_API_TOKEN}
    deadline = time.time() + timeout_secs
    while time.time() < deadline:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            raise ApifyError(f"Poll error: {r.status_code}")
        data = r.json()["data"]
        status = data["status"]
        if status == "SUCCEEDED":
            return data["defaultDatasetId"]
        if status in ("FAILED", "ABORTED", "TIMED-OUT"):
            raise ApifyError(f"Actor run {status}")
        time.sleep(5)
    raise ApifyError(f"Actor timed out after {timeout_secs}s")


def _get_dataset(dataset_id: str) -> list:
    """Fetch all items from a dataset."""
    url = f"{BASE}/datasets/{dataset_id}/items"
    params = {"token": APIFY_API_TOKEN, "clean": "true"}
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        raise ApifyError(f"Dataset fetch error: {r.status_code}")
    return r.json()


def _check_quota():
    remaining = get_remaining("apify")
    if not remaining["ok"]:
        raise ApifyQuotaError(
            f"Apify monthly limit reached ({remaining['used_month']}/{remaining['limit_month']})"
        )


def _extract_hashtags(caption: str) -> list:
    return list(set(re.findall(r"#(\w+)", caption or "")))


def _extract_mentions(caption: str) -> list:
    return list(set(re.findall(r"@(\w+)", caption or "")))


def _parse_timestamp(ts) -> str:
    """Convert epoch int or ISO string to ISO format string."""
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return str(ts)


def scrape_profile(username: str) -> dict:
    """
    Fetch public profile data for one Instagram username.
    Returns standardised profile dict. Raises ApifyQuotaError if quota hit.
    """
    _check_quota()
    _log(f"Scraping profile: @{username}")
    input_data = {
        "usernames": [username],
        "resultsType": "details",
        "resultsLimit": 1,
    }
    try:
        run_id = _run_actor(input_data)
        dataset_id = _wait_for_run(run_id)
        items = _get_dataset(dataset_id)
        increment("apify")
        if not items:
            _log(f"No data returned for @{username}")
            return None
        raw = items[0]
        return {
            "username":        raw.get("username", username),
            "fullName":        raw.get("fullName", ""),
            "followersCount":  int(raw.get("followersCount", 0)),
            "followingCount":  int(raw.get("followingCount", 0)),
            "postsCount":      int(raw.get("postsCount", 0)),
            "biography":       raw.get("biography", ""),
            "verified":        bool(raw.get("verified", False)),
            "profilePicUrl":   raw.get("profilePicUrl", ""),
            "externalUrl":     raw.get("externalUrl", ""),
        }
    except ApifyQuotaError:
        raise
    except Exception as e:
        raise ApifyError(f"Profile scrape failed for @{username}: {e}")


def scrape_reels(username: str, count: int = 12) -> list:
    """
    Fetch last `count` reels for a username.
    Returns list of standardised reel dicts. Raises ApifyQuotaError if quota hit.
    """
    _check_quota()
    _log(f"Scraping {count} reels: @{username}")
    # The actor returns richer post data when called via direct profile/reels URL.
    # Request more than `count` because non-video posts can be present in the feed.
    results_limit = min(max(count * 3, count), 50)
    input_data = {
        "directUrls":   [f"https://www.instagram.com/{username}/reels/"],
        "resultsType":  "posts",
        "resultsLimit": results_limit,
    }
    try:
        run_id = _run_actor(input_data)
        dataset_id = _wait_for_run(run_id)
        items = _get_dataset(dataset_id)
        increment("apify")
        reels = []
        for raw in items:
            # Only include video posts
            if raw.get("type") not in ("Video", "video") and not raw.get("isVideo"):
                continue
            caption   = raw.get("caption", "") or ""
            shortcode = raw.get("shortCode", raw.get("id", ""))
            canonical_url = raw.get("url", "")
            reel = {
                "shortcode":      shortcode,
                "caption":        caption,
                "likesCount":     int(raw.get("likesCount", 0)),
                "commentsCount":  int(raw.get("commentsCount", 0)),
                "videoViewCount": int(raw.get("videoViewCount", raw.get("playCount", 0))),
                "videoPlayCount": int(raw.get("videoPlayCount", raw.get("playCount", 0))),
                "timestamp":      _parse_timestamp(raw.get("timestamp")),
                "durationSec":    float(raw.get("videoDuration", 0) or 0),
                "displayUrl":     raw.get("displayUrl", ""),
                "reel_url":       canonical_url or f"https://www.instagram.com/reel/{shortcode}/",
                "hashtags":       _extract_hashtags(caption),
                "mentions":       _extract_mentions(caption),
            }
            reels.append(reel)
            if len(reels) >= count:
                break
        _log(f"Got {len(reels)} reels for @{username}")
        return reels
    except ApifyQuotaError:
        raise
    except Exception as e:
        raise ApifyError(f"Reels scrape failed for @{username}: {e}")
