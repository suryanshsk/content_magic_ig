"""
scrapers/rapidapi_scraper.py
Fallback Instagram scraper using RapidAPI Instagram Scraper API v2.
Free tier: 500 calls/month. Same output schema as apify_scraper.py.
"""

import re
import requests
from datetime import datetime, timezone
from config import RAPIDAPI_KEY, RAPIDAPI_HOST, RAPIDAPI_BASE_URL
from storage.quota_tracker import increment, get_remaining


class RapidAPIQuotaError(Exception):
    pass


class RapidAPIError(Exception):
    pass


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [RapidAPI] {msg}")


def _headers() -> dict:
    return {
        "x-rapidapi-key":  RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }


def _get(endpoint: str, params: dict = None) -> dict:
    url = f"{RAPIDAPI_BASE_URL}{endpoint}"
    try:
        r = requests.get(url, headers=_headers(), params=params or {}, timeout=20)
    except requests.exceptions.Timeout:
        raise RapidAPIError("Request timed out")
    except requests.exceptions.ConnectionError as e:
        raise RapidAPIError(f"Connection error: {e}")

    if r.status_code == 429:
        raise RapidAPIQuotaError("RapidAPI rate limit / quota exceeded (429)")
    if r.status_code == 401:
        raise RapidAPIError("RapidAPI unauthorised — check your API key")
    if r.status_code != 200:
        raise RapidAPIError(f"HTTP {r.status_code}: {r.text[:200]}")
    try:
        return r.json()
    except Exception:
        raise RapidAPIError(f"Invalid JSON response: {r.text[:200]}")


def _check_quota():
    remaining = get_remaining("rapidapi")
    if not remaining["ok"]:
        raise RapidAPIQuotaError(
            f"RapidAPI monthly limit reached ({remaining['used_month']}/{remaining['limit_month']})"
        )


def _extract_hashtags(caption: str) -> list:
    return list(set(re.findall(r"#(\w+)", caption or "")))


def _extract_mentions(caption: str) -> list:
    return list(set(re.findall(r"@(\w+)", caption or "")))


def _parse_timestamp(ts) -> str:
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
    return str(ts)


def scrape_profile(username: str) -> dict:
    """
    Fetch public profile data for one Instagram username via RapidAPI.
    Returns standardised profile dict matching apify_scraper output schema.
    """
    _check_quota()
    _log(f"Scraping profile: @{username}")
    try:
        data = _get("/info", {"username_or_id_or_url": username})
        increment("rapidapi")
        raw = data.get("data", data)
        return {
            "username":        raw.get("username", username),
            "fullName":        raw.get("full_name", raw.get("fullName", "")),
            "followersCount":  int(raw.get("follower_count", raw.get("followersCount", 0))),
            "followingCount":  int(raw.get("following_count", raw.get("followingCount", 0))),
            "postsCount":      int(raw.get("media_count", raw.get("postsCount", 0))),
            "biography":       raw.get("biography", ""),
            "verified":        bool(raw.get("is_verified", raw.get("verified", False))),
            "profilePicUrl":   raw.get("profile_pic_url_hd", raw.get("profile_pic_url", "")),
            "externalUrl":     raw.get("external_url", ""),
        }
    except RapidAPIQuotaError:
        raise
    except RapidAPIError:
        raise
    except Exception as e:
        raise RapidAPIError(f"Profile scrape failed for @{username}: {e}")


def scrape_reels(username: str, count: int = 12) -> list:
    """
    Fetch last `count` reels for a username via RapidAPI.
    Returns list of standardised reel dicts matching apify_scraper output schema.
    """
    _check_quota()
    _log(f"Scraping {count} reels: @{username}")
    try:
        data = _get("/posts", {
            "username_or_id_or_url": username,
            "type": "video",
        })
        increment("rapidapi")
        items = data.get("data", {}).get("items", data.get("items", []))
        reels = []
        for raw in items[:count]:
            caption_raw = raw.get("caption", {})
            if isinstance(caption_raw, dict):
                caption = caption_raw.get("text", "")
            else:
                caption = str(caption_raw or "")

            shortcode = raw.get("code", raw.get("shortcode", raw.get("id", "")))
            media_type = raw.get("media_type", 0)
            # 2 = video on RapidAPI schema
            if media_type not in (2, "2", "video", "Video") and not raw.get("is_video"):
                continue

            video_versions = raw.get("video_versions", [{}])
            duration = float(raw.get("video_duration", 0) or 0)
            view_count = int(
                raw.get("play_count",
                raw.get("view_count",
                raw.get("video_view_count", 0))) or 0
            )
            like_count = int(
                raw.get("like_count",
                raw.get("likes", {}).get("count", 0)) or 0
            )
            comment_count = int(
                raw.get("comment_count",
                raw.get("comments", {}).get("count", 0)) or 0
            )
            taken_at = raw.get("taken_at", raw.get("timestamp"))

            reel = {
                "shortcode":      str(shortcode),
                "caption":        caption,
                "likesCount":     like_count,
                "commentsCount":  comment_count,
                "videoViewCount": view_count,
                "videoPlayCount": view_count,
                "timestamp":      _parse_timestamp(taken_at),
                "durationSec":    duration,
                "displayUrl":     (video_versions[0].get("url", "") if video_versions else
                                   raw.get("thumbnail_url", raw.get("display_url", ""))),
                "reel_url":       f"https://www.instagram.com/reel/{shortcode}/",
                "hashtags":       _extract_hashtags(caption),
                "mentions":       _extract_mentions(caption),
            }
            reels.append(reel)

        _log(f"Got {len(reels)} reels for @{username}")
        return reels
    except RapidAPIQuotaError:
        raise
    except RapidAPIError:
        raise
    except Exception as e:
        raise RapidAPIError(f"Reels scrape failed for @{username}: {e}")
