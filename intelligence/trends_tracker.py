"""
intelligence/trends_tracker.py
Fetches real Google Trends data for India using pytrends (100% free, no API key).
Combines interest-over-time, rising queries, daily trending, and realtime trending.
"""

import time
from datetime import datetime
from pytrends.request import TrendReq
from config import NICHE_KEYWORDS


def _log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Trends] {msg}")


TECH_FILTER = [
    "ai", "python", "code", "coding", "app", "tech", "data",
    "startup", "software", "developer", "machine", "learning",
    "devops", "cloud", "llm", "gpt", "openai", "api", "programming",
    "engineer", "ml", "deep learning", "neural", "automation",
]


def _is_tech(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in TECH_FILTER)


def _pytrends() -> TrendReq:
    return TrendReq(hl="en-IN", tz=330, timeout=(10, 25), retries=2, backoff_factor=0.5)


def get_keyword_scores(keywords: list) -> list:
    """
    Get interest-over-time scores for up to 5 keywords.
    Returns list of dicts with score, 7d avg, direction.
    """
    results = []
    pt = _pytrends()
    try:
        pt.build_payload(keywords[:5], timeframe="now 7-d", geo="IN")
        df = pt.interest_over_time()
        if df.empty:
            return results
        for kw in keywords[:5]:
            if kw not in df.columns:
                continue
            series  = df[kw]
            current = int(series.iloc[-1])
            avg_7d  = round(float(series.mean()), 1)
            peak    = int(series.max())
            direction = "rising" if current > avg_7d else "falling"
            results.append({
                "keyword":   kw,
                "score":     current,
                "avg_7d":    avg_7d,
                "peak":      peak,
                "direction": direction,
                "type":      "niche_keyword",
                "region":    "India",
                "timestamp": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        _log(f"Keyword scores error: {e}")
    return results


def get_rising_queries(seed_keywords: list) -> list:
    """
    Get rising related queries for seed keywords.
    Returns top 10 rising tech-related queries.
    """
    results = []
    pt = _pytrends()
    for kw in seed_keywords[:3]:
        try:
            pt.build_payload([kw], timeframe="now 7-d", geo="IN")
            related = pt.related_queries()
            rising_df = related.get(kw, {}).get("rising")
            if rising_df is not None and not rising_df.empty:
                for _, row in rising_df.head(5).iterrows():
                    query = str(row.get("query", ""))
                    if _is_tech(query):
                        results.append({
                            "keyword":   query,
                            "score":     min(100, int(row.get("value", 50))),
                            "direction": "rising",
                            "type":      "rising_query",
                            "parent":    kw,
                            "region":    "India",
                            "timestamp": datetime.utcnow().isoformat(),
                        })
            time.sleep(1)
        except Exception as e:
            _log(f"Rising queries error for '{kw}': {e}")
    return results[:10]


def get_daily_trending_india() -> list:
    """
    Get today's trending searches in India filtered for tech topics.
    """
    results = []
    pt = _pytrends()
    try:
        df = pt.trending_searches(pn="india")
        for i, row in df.head(30).iterrows():
            topic = str(row.iloc[0])
            if _is_tech(topic):
                results.append({
                    "keyword":   topic,
                    "score":     max(10, 100 - i * 3),
                    "direction": "trending",
                    "type":      "daily_trending_india",
                    "region":    "India",
                    "timestamp": datetime.utcnow().isoformat(),
                })
        time.sleep(1)
    except Exception as e:
        _log(f"Daily trending error: {e}")
    return results[:10]


def get_realtime_trending() -> list:
    """
    Get realtime trending searches in India filtered for tech.
    """
    results = []
    pt = _pytrends()
    try:
        df = pt.realtime_trending_searches(pn="IN")
        if df is None or df.empty:
            return results
        for _, row in df.head(20).iterrows():
            title = str(row.get("title", ""))
            if _is_tech(title):
                results.append({
                    "keyword":   title[:100],
                    "score":     85,
                    "direction": "realtime",
                    "type":      "realtime_trending",
                    "region":    "India",
                    "timestamp": datetime.utcnow().isoformat(),
                })
        time.sleep(1)
    except Exception as e:
        _log(f"Realtime trending error: {e}")
    return results[:10]


def get_all_trends() -> list:
    """
    Fetch all trend sources, merge, deduplicate, sort by score.
    This is the only function other modules should call.
    """
    _log("Fetching all Google Trends data for India...")
    all_results = []

    # Batch keywords into groups of 5 (pytrends limit)
    kw_batches = [NICHE_KEYWORDS[i:i+5] for i in range(0, len(NICHE_KEYWORDS), 5)]
    for batch in kw_batches:
        scores = get_keyword_scores(batch)
        all_results.extend(scores)
        time.sleep(1)

    rising = get_rising_queries(NICHE_KEYWORDS[:5])
    all_results.extend(rising)
    time.sleep(1)

    daily = get_daily_trending_india()
    all_results.extend(daily)
    time.sleep(1)

    realtime = get_realtime_trending()
    all_results.extend(realtime)

    # Deduplicate by keyword (case-insensitive)
    seen     = set()
    deduped  = []
    for item in all_results:
        key = item["keyword"].lower().strip()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    sorted_results = sorted(deduped, key=lambda x: x["score"], reverse=True)
    _log(f"Found {len(sorted_results)} unique trending items")
    return sorted_results
