"""
scrapers/rapidapi_scraper.py
Fallback Instagram scraper using RapidAPI Instagram APIs.
Supports both legacy and stable endpoint/response shapes.
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


def _headers(content_type_json: bool = True) -> dict:
    key = (RAPIDAPI_KEY or "").strip().strip('"').strip("'")
    host = (RAPIDAPI_HOST or "").strip().strip('"').strip("'")
    headers = {
        "x-rapidapi-key":  key,
        "x-rapidapi-host": host,
    }
    if content_type_json:
        headers["content-type"] = "application/json"
    return headers


def _request(
    method: str,
    endpoint: str,
    params: dict = None,
    json_body: dict = None,
    form_body: dict = None,
) -> dict:
    url = f"{RAPIDAPI_BASE_URL}{endpoint}"
    try:
        if method.upper() == "POST":
            if form_body is not None:
                r = requests.post(
                    url,
                    headers=_headers(content_type_json=False),
                    params=params or {},
                    data=form_body,
                    timeout=25,
                )
            else:
                r = requests.post(
                    url,
                    headers=_headers(content_type_json=True),
                    params=params or {},
                    json=json_body or {},
                    timeout=25,
                )
        else:
            r = requests.get(url, headers=_headers(content_type_json=True), params=params or {}, timeout=25)
    except requests.exceptions.Timeout:
        raise RapidAPIError("Request timed out")
    except requests.exceptions.ConnectionError as e:
        raise RapidAPIError(f"Connection error: {e}")

    if r.status_code == 429:
        raise RapidAPIQuotaError("RapidAPI rate limit / quota exceeded (429)")
    if r.status_code == 401:
        raise RapidAPIError("RapidAPI unauthorized (401) — key may be invalid or revoked")
    if r.status_code != 200:
        msg = r.text[:200]
        if "Invalid API key" in msg:
            raise RapidAPIError("RapidAPI invalid key — rotate key and update RAPIDAPI_KEY")
        if "not subscribed" in msg.lower():
            raise RapidAPIError("RapidAPI key is valid but not subscribed to configured API host")
        raise RapidAPIError(f"HTTP {r.status_code}: {msg}")
    try:
        payload = r.json()
    except ValueError:
        raise RapidAPIError(f"Invalid JSON response: {r.text[:200]}")

    if isinstance(payload, dict):
        err = str(payload.get("error", "") or payload.get("message", ""))
        if err and "please try again later" in err.lower():
            raise RapidAPIError("RapidAPI provider temporary error: Please try again later")
    return payload


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


def _first_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, list) and value and isinstance(value[0], dict):
        return value[0]
    return {}


def _extract_profile_payload(data: dict) -> dict:
    candidates = [
        data.get("data"),
        (data.get("reels") or [{}])[0] if isinstance(data.get("reels"), list) and data.get("reels") else None,
        data.get("user"),
        data.get("result"),
        data,
    ]
    for c in candidates:
        raw = _first_dict(c)
        if raw.get("username") or raw.get("full_name") or raw.get("follower_count"):
            return raw
    return _first_dict(data.get("data")) or data


def _extract_posts_payload(data: dict) -> list:
    candidates = [
        data.get("reels"),
        data.get("data", {}).get("items") if isinstance(data.get("data"), dict) else None,
        data.get("items"),
        data.get("data"),
        data.get("result"),
    ]
    for c in candidates:
        if isinstance(c, list):
            return c
    return []


def _get_profile_data(username: str) -> dict:
    profile_url = f"https://www.instagram.com/{username}/"
    attempts = [
        ("POST", "/get_ig_user_reels.php", None, None, {"username": username, "amount": "1", "pagination_token": ""}),
        ("POST", "/get_ig_user_followers_v2.php", None, None, {"username_or_url": profile_url, "data": "following", "amount": "1", "pagination_token": ""}),
        ("GET", "/info", {"username_or_id_or_url": username}, None),
        ("GET", "/userinfo", {"username_or_url": profile_url}, None),
        ("GET", "/user-info", {"username_or_url": profile_url}, None),
        ("POST", "/userinfo", None, {"username_or_url": profile_url}),
        ("POST", "/user-info", None, {"username_or_url": profile_url}),
    ]
    last_error = None
    for attempt in attempts:
        if len(attempt) == 5:
            method, endpoint, params, body, form_body = attempt
        else:
            method, endpoint, params, body = attempt
            form_body = None
        try:
            return _request(method, endpoint, params=params, json_body=body, form_body=form_body)
        except RapidAPIError as e:
            last_error = e
            continue
    raise RapidAPIError(f"Profile endpoint attempts failed: {last_error}")


def _get_posts_data(username: str, count: int) -> dict:
    profile_url = f"https://www.instagram.com/{username}/"
    attempts = [
        (
            "POST",
            "/get_ig_user_reels.php",
            None,
            None,
            {
                "username": username,
                "amount": str(min(max(count, 1), 50)),
                "pagination_token": "",
            },
        ),
        (
            "POST",
            "/get_ig_user_posts.php",
            None,
            None,
            {
                "username": username,
                "amount": str(min(max(count, 1), 50)),
                "pagination_token": "",
            },
        ),
        ("GET", "/posts", {"username_or_id_or_url": username, "type": "video"}, None),
        ("GET", "/posts", {"username_or_url": profile_url, "data": "following", "amount": min(max(count, 1), 50)}, None),
        ("POST", "/posts", None, {"username_or_url": profile_url, "data": "following", "amount": min(max(count, 1), 50)}),
        ("GET", "/reels", {"username_or_url": profile_url, "amount": min(max(count, 1), 50)}, None),
    ]
    last_error = None
    for attempt in attempts:
        if len(attempt) == 5:
            method, endpoint, params, body, form_body = attempt
        else:
            method, endpoint, params, body = attempt
            form_body = None
        try:
            return _request(method, endpoint, params=params, json_body=body, form_body=form_body)
        except RapidAPIError as e:
            last_error = e
            continue
    raise RapidAPIError(f"Reels/posts endpoint attempts failed: {last_error}")


def scrape_profile(username: str) -> dict:
    """
    Fetch public profile data for one Instagram username via RapidAPI.
    Returns standardised profile dict matching apify_scraper output schema.
    """
    _check_quota()
    _log(f"Scraping profile: @{username}")
    try:
        data = _get_profile_data(username)
        increment("rapidapi")
        raw = _extract_profile_payload(data)
        # Stable API reels endpoint returns profile details under reels[0].node.media.user
        if isinstance(data, dict) and isinstance(data.get("reels"), list) and data.get("reels"):
            first = data["reels"][0]
            node = first.get("node", {}) if isinstance(first, dict) else {}
            media = node.get("media", {}) if isinstance(node, dict) else {}
            user = media.get("user", {}) if isinstance(media, dict) else {}
            if user:
                raw = {
                    **raw,
                    "username": user.get("username", username),
                    "full_name": user.get("full_name", ""),
                    "is_verified": user.get("is_verified", False),
                    "profile_pic_url": user.get("profile_pic_url", ""),
                }
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
        data = _get_posts_data(username, count)
        increment("rapidapi")
        items = _extract_posts_payload(data)
        reels = []
        for raw in items[:count]:
            if isinstance(raw, dict) and isinstance(raw.get("node"), dict):
                raw = raw.get("node", {}).get("media", raw)

            caption_raw = raw.get("caption", {})
            if isinstance(caption_raw, dict):
                caption = caption_raw.get("text", "")
            else:
                caption = str(caption_raw or "")

            shortcode = raw.get("code", raw.get("shortcode", raw.get("id", "")))
            media_type = raw.get("media_type", 0)
            # 2 = video on RapidAPI schema
            is_video = bool(raw.get("is_video") or raw.get("isVideo") or raw.get("video_url"))
            if media_type not in (2, "2", "video", "Video") and not is_video:
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
                                   raw.get("thumbnail_url", raw.get("display_url", raw.get("image_url", "")))),
                "reel_url":       raw.get("permalink", raw.get("url", f"https://www.instagram.com/reel/{shortcode}/")),
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
