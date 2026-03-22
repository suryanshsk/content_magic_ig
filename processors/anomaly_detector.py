"""
processors/anomaly_detector.py
Detects all anomaly types: viral spikes, posting gaps, follower spikes,
engagement drops, posting frequency changes. Input: current + historical data.
"""

from datetime import datetime, timezone, timedelta
from statistics import mean
from processors.metrics import _parse_dt


def detect_viral_spike(reels: list, avg_views: float,
                        multiplier: float = 2.0) -> list:
    """
    Return list of reels that exceed avg_views * multiplier.
    Each anomaly includes full reel context for Telegram alert.
    """
    anomalies = []
    if avg_views <= 0:
        return anomalies

    for reel in reels:
        views = reel.get("videoViewCount", 0)
        if views >= avg_views * multiplier:
            caption  = reel.get("caption", "")
            hook     = caption[:120].split("\n")[0].strip() if caption else ""
            anomalies.append({
                "type":        "VIRAL_SPIKE",
                "severity":    "high",
                "reel_url":    reel.get("reel_url", ""),
                "shortcode":   reel.get("shortcode", ""),
                "title":       caption[:80],
                "hook":        hook,
                "views":       views,
                "avg_views":   round(avg_views),
                "multiplier":  round(views / avg_views, 2),
                "likes":       reel.get("likesCount", 0),
                "comments":    reel.get("commentsCount", 0),
                "hashtags":    reel.get("hashtags", []),
                "posted_at":   reel.get("timestamp", ""),
            })
    return anomalies


def detect_posting_spike(posts_this_week: int,
                          usual_weekly_avg: float) -> dict | None:
    """
    Detects if creator posted 3x more than their usual weekly avg.
    Returns anomaly dict or None.
    """
    if usual_weekly_avg <= 0 or posts_this_week < 3:
        return None
    if posts_this_week >= usual_weekly_avg * 3:
        return {
            "type":     "POSTING_SPIKE",
            "severity": "medium",
            "detail":   (
                f"Posted {posts_this_week} times this week "
                f"vs usual avg of {round(usual_weekly_avg, 1)}/week"
            ),
        }
    return None


def detect_posting_gap(reels: list, usual_frequency_days: float) -> dict | None:
    """
    Detects if creator hasn't posted in 2x their usual frequency.
    Returns anomaly dict or None.
    """
    if usual_frequency_days <= 0 or not reels:
        return None
    now = datetime.now(timezone.utc)
    latest = max(_parse_dt(r["timestamp"]) for r in reels)
    days_since = (now - latest).total_seconds() / 86400
    if days_since >= usual_frequency_days * 2:
        return {
            "type":     "POSTING_GAP",
            "severity": "low",
            "detail":   (
                f"No post for {round(days_since, 1)} days "
                f"(usual: every {usual_frequency_days} days)"
            ),
        }
    return None


def detect_follower_spike(current_followers: int,
                           previous_followers: int) -> dict | None:
    """
    Detects if followers grew 5%+ since last scrape.
    Returns anomaly dict or None.
    """
    if previous_followers <= 0:
        return None
    growth = (current_followers - previous_followers) / previous_followers
    if growth >= 0.05:
        gained = current_followers - previous_followers
        return {
            "type":     "FOLLOWER_SPIKE",
            "severity": "high",
            "detail":   (
                f"Gained {gained:,} followers "
                f"({round(growth * 100, 1)}% growth)"
            ),
        }
    return None


def detect_engagement_drop(current_rate: float,
                            avg_30d_rate: float) -> dict | None:
    """
    Detects if engagement rate dropped 30%+ vs 30-day average.
    Returns anomaly dict or None.
    """
    if avg_30d_rate <= 0:
        return None
    drop = (avg_30d_rate - current_rate) / avg_30d_rate
    if drop >= 0.30:
        return {
            "type":     "ENGAGEMENT_DROP",
            "severity": "medium",
            "detail":   (
                f"Engagement dropped to {round(current_rate, 2)}% "
                f"from 30d avg of {round(avg_30d_rate, 2)}% "
                f"(−{round(drop * 100, 1)}%)"
            ),
        }
    return None


def run_all_checks(creator_data: dict, historical_data: list,
                   metrics: dict) -> list:
    """
    Run all anomaly checks for one creator.
    creator_data: {"profile": {...}, "reels": [...]}
    historical_data: list of previous metric rows from Sheets
    metrics: computed metrics dict from metrics.py
    Returns flat list of all anomaly dicts found.
    """
    anomalies = []
    profile = creator_data.get("profile", {})
    reels   = creator_data.get("reels", [])

    avg_views  = metrics.get("avg_views", 0)
    eng_rate   = metrics.get("engagement_rate", 0)
    posts_week = metrics.get("posts_this_week", 0)
    freq_days  = metrics.get("posting_frequency_days", 0)

    # 1. Viral spikes
    viral = detect_viral_spike(reels, avg_views)
    anomalies.extend(viral)

    # 2. Posting spike — compare to historical weekly avg
    if historical_data:
        hist_weekly = [
            float(row.get("PostsThisWeek", 0))
            for row in historical_data
            if row.get("PostsThisWeek")
        ]
        usual_weekly = mean(hist_weekly) if hist_weekly else 0
        spike = detect_posting_spike(posts_week, usual_weekly)
        if spike:
            anomalies.append(spike)

    # 3. Posting gap
    gap = detect_posting_gap(reels, freq_days)
    if gap:
        anomalies.append(gap)

    # 4. Follower spike — compare to previous scrape
    if historical_data:
        prev_followers = int(historical_data[-1].get("Followers", 0))
        curr_followers = profile.get("followersCount", 0)
        fspike = detect_follower_spike(curr_followers, prev_followers)
        if fspike:
            anomalies.append(fspike)

    # 5. Engagement drop — compare to 30-day average
    if historical_data:
        hist_eng = [
            float(row.get("EngagementRate", 0))
            for row in historical_data
            if row.get("EngagementRate")
        ]
        avg_30d_eng = mean(hist_eng) if hist_eng else 0
        edrop = detect_engagement_drop(eng_rate, avg_30d_eng)
        if edrop:
            anomalies.append(edrop)

    return anomalies
