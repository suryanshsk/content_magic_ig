"""
processors/metrics.py
Computes all engagement metrics and posting analytics from raw scraped data.
Input: raw profile dict + reels list. Output: metrics dict.
"""

import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from statistics import mean


def _parse_dt(ts: str) -> datetime:
    """Parse ISO timestamp string to timezone-aware datetime."""
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return datetime.now(timezone.utc)


def _first_sentence(text: str, max_chars: int = 120) -> str:
    """Extract hook — first meaningful line of a caption."""
    if not text:
        return ""
    text = text.strip()
    # Cut at newline or sentence end
    for sep in ["\n", ".", "!", "?"]:
        idx = text.find(sep)
        if 0 < idx <= max_chars:
            return text[:idx].strip()
    return text[:max_chars].strip()


def calculate_creator_metrics(profile: dict, reels: list) -> dict:
    """
    Compute full metrics dict for one creator.
    Returns zeros gracefully when reels list is empty.
    """
    followers = int(profile.get("followersCount", 0))
    now       = datetime.now(timezone.utc)
    week_ago  = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    if not reels:
        return {
            "username":           profile.get("username", ""),
            "followers":          followers,
            "avg_views":          0,
            "avg_likes":          0,
            "avg_comments":       0,
            "engagement_rate":    0.0,
            "posts_this_week":    0,
            "posts_this_month":   0,
            "best_reel":          None,
            "worst_reel":         None,
            "most_used_hashtags": [],
            "avg_caption_length": 0,
            "avg_duration_secs":  0.0,
            "best_posting_hour":  None,
            "best_posting_day":   None,
            "posting_frequency_days": 0.0,
            "no_reels":           True,
        }

    views    = [r.get("videoViewCount", 0) for r in reels]
    likes    = [r.get("likesCount", 0)     for r in reels]
    comments = [r.get("commentsCount", 0)  for r in reels]

    avg_views    = mean(views)    if views    else 0
    avg_likes    = mean(likes)    if likes    else 0
    avg_comments = mean(comments) if comments else 0

    engagement_rate = (
        (avg_likes + avg_comments) / followers * 100
        if followers > 0 else 0.0
    )

    # Posts in window
    posts_this_week  = sum(1 for r in reels if _parse_dt(r["timestamp"]) >= week_ago)
    posts_this_month = sum(1 for r in reels if _parse_dt(r["timestamp"]) >= month_ago)

    # Best / worst reels
    best_reel  = max(reels, key=lambda r: r.get("videoViewCount", 0))
    worst_reel = min(reels, key=lambda r: r.get("videoViewCount", 0))

    # Hashtag frequency
    all_tags = []
    for r in reels:
        all_tags.extend(r.get("hashtags", []))
    top_hashtags = [tag for tag, _ in Counter(all_tags).most_common(5)]

    # Caption length
    caption_lengths = [len(r.get("caption", "")) for r in reels]
    avg_caption_length = int(mean(caption_lengths)) if caption_lengths else 0

    # Duration
    durations = [r.get("durationSec", 0) for r in reels if r.get("durationSec")]
    avg_duration_secs = round(mean(durations), 1) if durations else 0.0

    # Best posting time — from top 3 reels by views
    top3 = sorted(reels, key=lambda r: r.get("videoViewCount", 0), reverse=True)[:3]
    hours = [_parse_dt(r["timestamp"]).hour for r in top3]
    days  = [_parse_dt(r["timestamp"]).strftime("%A") for r in top3]
    best_posting_hour = Counter(hours).most_common(1)[0][0] if hours else None
    best_posting_day  = Counter(days).most_common(1)[0][0]  if days  else None

    # Posting frequency
    posting_frequency_days = compute_posting_frequency(reels)

    return {
        "username":               profile.get("username", ""),
        "followers":              followers,
        "avg_views":              round(avg_views),
        "avg_likes":              round(avg_likes),
        "avg_comments":           round(avg_comments),
        "engagement_rate":        round(engagement_rate, 2),
        "posts_this_week":        posts_this_week,
        "posts_this_month":       posts_this_month,
        "best_reel":              best_reel,
        "worst_reel":             worst_reel,
        "most_used_hashtags":     top_hashtags,
        "avg_caption_length":     avg_caption_length,
        "avg_duration_secs":      avg_duration_secs,
        "best_posting_hour":      best_posting_hour,
        "best_posting_day":       best_posting_day,
        "posting_frequency_days": posting_frequency_days,
        "no_reels":               False,
    }


def compute_posting_frequency(reels: list) -> float:
    """Average days between posts. Returns 0 if fewer than 2 reels."""
    if len(reels) < 2:
        return 0.0
    timestamps = sorted([_parse_dt(r["timestamp"]) for r in reels], reverse=True)
    gaps = [
        (timestamps[i] - timestamps[i + 1]).total_seconds() / 86400
        for i in range(len(timestamps) - 1)
    ]
    return round(mean(gaps), 1) if gaps else 0.0


def extract_top_hooks(reels: list, top_n: int = 3) -> list:
    """
    Return hook text from top N reels by views.
    Hook = first meaningful sentence of caption.
    """
    sorted_reels = sorted(reels, key=lambda r: r.get("videoViewCount", 0), reverse=True)
    hooks = []
    for r in sorted_reels[:top_n]:
        caption = r.get("caption", "")
        hook = _first_sentence(caption)
        if hook:
            hooks.append(hook)
    return hooks
