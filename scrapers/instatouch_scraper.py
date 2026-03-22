"""
Optional tertiary Instagram fallback via InstaTouch CLI (Node.js).
Used only when Apify + RapidAPI are unavailable or rate-limited.
"""

import glob
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone

from config import (
    INSTATOUCH_NPX_COMMAND,
    INSTATOUCH_SESSION,
    INSTATOUCH_TIMEOUT_MS,
    AUTO_FETCH_INSTAGRAM_SESSION,
    INSTATOUCH_MAX_CREATORS_PER_RUN,
    INSTATOUCH_COOLDOWN_SECONDS,
)


class InstaTouchError(Exception):
    pass


class InstaTouchRateLimitError(InstaTouchError):
    pass


_CACHED_SESSION = ""
_LAST_CALL_TS = 0.0
_POSTS_CACHE: dict[str, list] = {}
_USED_USERNAMES: set[str] = set()


def _log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [InstaTouch] {msg}")


def _epoch_to_iso(ts) -> str:
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


def _extract_hashtags(caption: str) -> list:
    return list(set(re.findall(r"#(\w+)", caption or "")))


def _extract_mentions(caption: str) -> list:
    return list(set(re.findall(r"@(\w+)", caption or "")))


def _load_collector(json_file: str):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("collector"), list):
            return data["collector"]
    return []


def _normalize_session(raw: str) -> str:
    token = (raw or "").strip()
    if not token:
        return ""
    if token.lower().startswith("sessionid="):
        return token
    return f"sessionid={token}"


def _fetch_session_from_browser() -> str:
    if not AUTO_FETCH_INSTAGRAM_SESSION:
        return ""

    try:
        import browser_cookie3  # type: ignore
    except Exception as e:
        raise InstaTouchError(
            "Auto Instagram session fetch needs 'browser-cookie3'. "
            f"Install dependencies first. ({e})"
        )

    browsers = [
        ("chrome", browser_cookie3.chrome),
        ("edge", browser_cookie3.edge),
        ("brave", getattr(browser_cookie3, "brave", None)),
    ]

    for browser_name, getter in browsers:
        if getter is None:
            continue
        try:
            jar = getter(domain_name=".instagram.com")
        except Exception:
            continue

        for cookie in jar:
            if cookie.name == "sessionid" and cookie.value:
                _log(f"Auto-fetched Instagram session from {browser_name}")
                return f"sessionid={cookie.value}"

    return ""


def _resolve_session() -> str:
    global _CACHED_SESSION
    if _CACHED_SESSION:
        return _CACHED_SESSION

    manual = _normalize_session(INSTATOUCH_SESSION)
    if manual:
        _CACHED_SESSION = manual
        return _CACHED_SESSION

    auto = _fetch_session_from_browser()
    if auto:
        _CACHED_SESSION = auto
        return _CACHED_SESSION

    return ""


def _ensure_safe_limits(username: str) -> None:
    # Hard cap limits impact on the logged-in session account in fallback mode.
    if username not in _USED_USERNAMES:
        if len(_USED_USERNAMES) >= max(1, INSTATOUCH_MAX_CREATORS_PER_RUN):
            raise InstaTouchError(
                f"InstaTouch safety cap reached ({INSTATOUCH_MAX_CREATORS_PER_RUN} creators/run)."
            )
        _USED_USERNAMES.add(username)


def _respect_cooldown() -> None:
    global _LAST_CALL_TS
    cooldown = max(0, int(INSTATOUCH_COOLDOWN_SECONDS))
    if cooldown <= 0:
        return
    elapsed = time.time() - _LAST_CALL_TS
    if elapsed < cooldown:
        time.sleep(cooldown - elapsed)
    _LAST_CALL_TS = time.time()


def _run_user_scrape(username: str, count: int) -> list:
    if username in _POSTS_CACHE and len(_POSTS_CACHE[username]) >= max(1, int(count)):
        return _POSTS_CACHE[username][:count]

    _ensure_safe_limits(username)
    _respect_cooldown()

    session = _resolve_session()
    if not session:
        raise InstaTouchError(
            "No Instagram session available. Set INSTATOUCH_SESSION in .env "
            "or enable AUTO_FETCH_INSTAGRAM_SESSION with active Chrome login."
        )

    out_dir = tempfile.mkdtemp(prefix="instatouch_")
    filename = f"{username}_{int(time.time())}"
    cmd = [
        INSTATOUCH_NPX_COMMAND,
        "-y",
        "instatouch",
        "user",
        username,
        "--count",
        str(max(1, int(count))),
        "--mediaType",
        "all",
        "--filetype",
        "json",
        "--filepath",
        out_dir,
        "--filename",
        filename,
        "--session",
        session,
        "--timeout",
        str(max(0, int(INSTATOUCH_TIMEOUT_MS))),
    ]

    _log(f"Running fallback scrape for @{username}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
    except FileNotFoundError as e:
        raise InstaTouchError(
            f"Could not run '{INSTATOUCH_NPX_COMMAND}'. Install Node.js and ensure npx is available. ({e})"
        )
    except subprocess.TimeoutExpired:
        raise InstaTouchError("InstaTouch command timed out")

    output = (result.stdout or "") + "\n" + (result.stderr or "")
    lowered = output.lower()
    if "rate limit" in lowered:
        raise InstaTouchRateLimitError("Instagram rate limit hit in InstaTouch")
    if result.returncode != 0:
        raise InstaTouchError(f"InstaTouch failed: {output[:300]}")

    matches = glob.glob(os.path.join(out_dir, f"{filename}.json"))
    if not matches:
        matches = glob.glob(os.path.join(out_dir, "*.json"))
    if not matches:
        raise InstaTouchError("InstaTouch did not produce JSON output")

    data = _load_collector(matches[0])
    _POSTS_CACHE[username] = data
    return data[:count]


def scrape_profile(username: str) -> dict:
    """
    Build a minimal profile from latest posts when direct profile fields are unavailable.
    """
    # Pull a larger slice once so scrape_reels can reuse cache and avoid extra requests.
    posts = _run_user_scrape(username, count=12)
    if not posts:
        return {
            "username": username,
            "fullName": "",
            "followersCount": 0,
            "followingCount": 0,
            "postsCount": 0,
            "biography": "",
            "verified": False,
            "profilePicUrl": "",
            "externalUrl": "",
        }

    first = posts[0]
    owner = first.get("owner", {}) if isinstance(first, dict) else {}
    return {
        "username": owner.get("username", username) or username,
        "fullName": "",
        "followersCount": 0,
        "followingCount": 0,
        "postsCount": 0,
        "biography": "",
        "verified": False,
        "profilePicUrl": owner.get("profile_pic_url", ""),
        "externalUrl": "",
    }


def scrape_reels(username: str, count: int = 12) -> list:
    posts = _run_user_scrape(username, count=count)
    reels = []
    for raw in posts:
        if not isinstance(raw, dict):
            continue

        is_video = bool(raw.get("is_video", False))
        if not is_video:
            continue

        caption = raw.get("description", "") or ""
        shortcode = raw.get("shortcode", raw.get("id", ""))
        reels.append(
            {
                "shortcode": shortcode,
                "caption": caption,
                "likesCount": int(raw.get("likes", 0) or 0),
                "commentsCount": int(raw.get("comments", 0) or 0),
                "videoViewCount": int(raw.get("video_view_count", 0) or 0),
                "videoPlayCount": int(raw.get("video_view_count", 0) or 0),
                "timestamp": _epoch_to_iso(raw.get("taken_at_timestamp")),
                "durationSec": float(raw.get("video_duration", 0) or 0),
                "displayUrl": raw.get("display_url", ""),
                "reel_url": f"https://www.instagram.com/reel/{shortcode}/" if shortcode else "",
                "hashtags": _extract_hashtags(caption),
                "mentions": _extract_mentions(caption),
            }
        )
        if len(reels) >= count:
            break

    _log(f"Got {len(reels)} reels for @{username}")
    return reels
