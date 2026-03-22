"""
reports/weekly_report.py
Compiles weekly stats from Google Sheets and generates a punchy
strategy report via Claude API. Sends to Telegram every Monday 8 AM.
"""

from datetime import datetime, timedelta
import anthropic
from config import CLAUDE_MODEL
from storage.sheets_db import (
    get_all_viral_reels, get_recent_trends,
    save_weekly_report,
)
from notifications.telegram_alerts import send_weekly_report


def _log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Report] {msg}")


def compile_weekly_stats(wb) -> dict:
    """
    Read last 7 days from Google Sheets and compile full stats dict.
    wb: gspread Spreadsheet object
    """
    _log("Compiling weekly stats from Sheets...")
    now       = datetime.now()
    week_ago  = now - timedelta(days=7)
    week_start = week_ago.strftime("%Y-%m-%d")
    week_end   = now.strftime("%Y-%m-%d")

    # Viral reels this week
    viral_reels = get_all_viral_reels(wb, days=7)
    total_viral = len(viral_reels)

    # Anomalies this week
    try:
        anomaly_rows = wb.worksheet("Anomalies Log").get_all_records()
        anomalies_week = [
            r for r in anomaly_rows
            if str(r.get("Timestamp", "")) >= week_start
        ]
        total_anomalies = len(anomalies_week)
        anomaly_breakdown = {}
        for r in anomalies_week:
            t = r.get("AnomalyType", "Unknown")
            anomaly_breakdown[t] = anomaly_breakdown.get(t, 0) + 1
    except Exception as e:
        _log(f"Anomaly read error: {e}")
        total_anomalies  = 0
        anomaly_breakdown = {}

    # Top creators by avg views
    try:
        metric_rows = wb.worksheet("Creator Metrics").get_all_records()
        this_week_metrics = [
            r for r in metric_rows
            if str(r.get("Timestamp", "")) >= week_start
        ]
        # Group by username, take max avg views
        creator_best = {}
        for r in this_week_metrics:
            u = r.get("Username", "")
            v = int(r.get("AvgViews", 0))
            if u and v > creator_best.get(u, {}).get("avg_views", 0):
                creator_best[u] = {
                    "name":      r.get("Username", ""),
                    "avg_views": v,
                    "eng_rate":  r.get("EngagementRate", 0),
                }
        top_3 = sorted(creator_best.values(),
                        key=lambda x: x["avg_views"], reverse=True)[:3]
        top_creator = top_3[0]["name"] if top_3 else ""
    except Exception as e:
        _log(f"Metrics read error: {e}")
        top_3        = []
        top_creator  = ""

    # Top trending topics
    try:
        trends = get_recent_trends(wb, hours=168)  # last 7 days
        trends_sorted = sorted(trends, key=lambda x: int(x.get("Score", 0)), reverse=True)
        top_5_topics  = trends_sorted[:5]
        top_topic     = top_5_topics[0].get("Keyword", "") if top_5_topics else ""
    except Exception as e:
        _log(f"Trends read error: {e}")
        top_5_topics = []
        top_topic    = ""

    # Ideas generated this week
    try:
        idea_rows = wb.worksheet("Content Ideas").get_all_records()
        ideas_week = [r for r in idea_rows if str(r.get("Date", "")) >= week_start]
        ideas_generated = len(ideas_week)
    except Exception as e:
        _log(f"Ideas read error: {e}")
        ideas_generated = 0

    # Creators tracked (unique usernames in Creator Profiles this week)
    try:
        profile_rows = wb.worksheet("Creator Profiles").get_all_records()
        week_profiles = [
            r for r in profile_rows
            if str(r.get("Timestamp", "")) >= week_start
        ]
        creators_tracked = len(set(r.get("Username", "") for r in week_profiles))
    except Exception:
        creators_tracked = 73

    return {
        "week_start":          week_start,
        "week_end":            week_end,
        "creators_tracked":    creators_tracked,
        "total_viral_spikes":  total_viral,
        "total_anomalies":     total_anomalies,
        "anomaly_breakdown":   anomaly_breakdown,
        "top_viral_creators":  top_3,
        "top_topics":          [
            {"keyword": t.get("Keyword",""), "score": int(t.get("Score",0))}
            for t in top_5_topics
        ],
        "top_creator":         top_creator,
        "top_topic":           top_topic,
        "ideas_generated":     ideas_generated,
        "viral_reels_sample":  viral_reels[:3],
    }


def build_action_plan(stats: dict) -> list:
    """
    Use Claude API to generate 3 concrete action items for next week.
    Returns list of 3 action strings.
    """
    _log("Generating action plan via Claude API...")
    top_topic   = stats.get("top_topic", "")
    top_creator = stats.get("top_creator", "")
    viral_count = stats.get("total_viral_spikes", 0)
    safe_topic = top_topic or "your fastest-growing niche topic"
    safe_creator = top_creator or "a top-performing creator"

    prompt = (
        f"@suryanshsk is an Indian tech creator (Coder + DevOps + AI/ML + Startups, 12.6K followers).\n"
        f"This week: {viral_count} viral spikes detected among 73 tracked creators.\n"
        f"Hottest topic: {safe_topic}\n"
        f"Most viral creator: {safe_creator}\n\n"
        f"Write exactly 3 short, specific, actionable bullet points for next week.\n"
        f"Each under 15 words. Direct, no fluff. Focus on content creation actions.\n"
        f"Return as plain text, one action per line, no numbering or bullets."
    )
    try:
        client  = anthropic.Anthropic()
        message = client.messages.create(
            model      = CLAUDE_MODEL,
            max_tokens = 200,
            messages   = [{"role": "user", "content": prompt}],
        )
        lines = [
            l.strip() for l in message.content[0].text.strip().splitlines()
            if l.strip()
        ]
        return lines[:3]
    except Exception as e:
        _log(f"Action plan error: {e}")
        return [
            f"Post one reel about '{safe_topic}' before Friday",
            f"Study hook style from {safe_creator}'s viral reels",
            "Post Monday + Friday at 7–9 PM IST for peak reach",
        ]


def run_weekly_report(wb) -> None:
    """
    Full pipeline: compile stats → build action plan → send Telegram → save Sheets.
    Call this every Monday at 8 AM IST.
    """
    _log("=== WEEKLY REPORT JOB STARTING ===")
    stats = compile_weekly_stats(wb)
    action_plan = build_action_plan(stats)
    stats["action_plan"] = action_plan

    # Send to Telegram
    sent = send_weekly_report(stats)
    _log(f"Weekly report Telegram: {'✅ sent' if sent else '❌ failed'}")

    # Save to Sheets
    try:
        save_weekly_report(wb, stats)
        _log("Weekly report saved to Sheets")
    except Exception as e:
        _log(f"Sheets save error: {e}")

    _log("=== WEEKLY REPORT DONE ===")
