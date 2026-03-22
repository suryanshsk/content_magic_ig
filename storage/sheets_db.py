"""
storage/sheets_db.py
Google Sheets as the free database. Creates 8 tabs, batch-saves all data.
Never calls append_row() in a loop — always uses append_rows() for batching.
"""

from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials
from config import GOOGLE_SHEETS_CREDS, SHEET_NAME, GOOGLE_SHEET_ID

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Sheet tab definitions: name → headers ───────────────────────────────────
SHEETS = {
    "Creator Profiles": [
        "Timestamp", "Username", "FullName", "Followers", "Following",
        "TotalPosts", "Verified", "Bio100", "ScrapedAt", "APIUsed",
    ],
    "Reel Stats": [
        "Timestamp", "CreatorUsername", "CreatorName", "ShortCode",
        "Caption100", "Views", "Likes", "Comments", "DurationSecs",
        "PostedAt", "DayOfWeek", "HourOfDay", "Hashtags", "ReelURL", "IsViral",
    ],
    "Creator Metrics": [
        "Timestamp", "Username", "Followers", "AvgViews", "AvgLikes",
        "AvgComments", "EngagementRate", "PostsThisWeek", "PostsThisMonth",
        "BestReelViews", "BestReelURL", "AvgCaptionLen", "AvgDurationSecs",
        "BestPostingHour", "BestPostingDay", "TopHashtags", "PostingFreqDays",
    ],
    "Viral Reels": [
        "Timestamp", "CreatorUsername", "CreatorName", "ReelURL",
        "Caption80", "Views", "Likes", "Comments", "Multiplier",
        "HookText", "HookPattern", "Hashtags", "PostedAt",
    ],
    "Anomalies Log": [
        "Timestamp", "CreatorUsername", "AnomalyType", "Severity",
        "Detail", "AlertSent", "ActionTaken",
    ],
    "Trending Topics": [
        "Timestamp", "Keyword", "Score", "Type", "Direction", "Region",
    ],
    "Content Ideas": [
        "Date", "HookText", "HookPattern", "HookScore", "IdeaTitle",
        "Urgency", "EstimatedViews", "WhyNow", "NicheAngle",
        "BestDay", "BestTime", "Hashtags", "Status",
    ],
    "Weekly Reports": [
        "WeekStart", "WeekEnd", "CreatorsTracked", "TotalViralSpikes",
        "TotalAnomalies", "TopCreator", "TopTopic", "IdeasGenerated", "Summary",
    ],
}


def _log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Sheets] {msg}")


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def connect() -> gspread.Client:
    creds = Credentials.from_service_account_file(GOOGLE_SHEETS_CREDS, scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_workbook(client: gspread.Client) -> gspread.Spreadsheet:
    if GOOGLE_SHEET_ID:
        try:
            wb = client.open_by_key(GOOGLE_SHEET_ID)
            _log(f"Opened workbook by ID: {GOOGLE_SHEET_ID}")
            return wb
        except Exception as e:
            _log(f"Open by sheet ID failed: {e}")

    try:
        wb = client.open(SHEET_NAME)
        _log(f"Opened existing workbook: {SHEET_NAME}")
        return wb
    except gspread.SpreadsheetNotFound:
        try:
            wb = client.create(SHEET_NAME)
            _log(f"Created new workbook: {SHEET_NAME}")
            return wb
        except Exception as e:
            raise RuntimeError(
                "Unable to open or create Google Sheet. "
                "Share an existing sheet with the service account and set "
                "GOOGLE_SHEET_NAME or GOOGLE_SHEET_ID in .env."
            ) from e


def setup_all_sheets(wb: gspread.Spreadsheet) -> None:
    """Create all required tabs with headers if they don't exist."""
    existing = {ws.title for ws in wb.worksheets()}
    for sheet_name, headers in SHEETS.items():
        if sheet_name not in existing:
            ws = wb.add_worksheet(title=sheet_name, rows=2000, cols=len(headers))
            ws.append_row(headers)
            ws.format("1:1", {
                "backgroundColor": {"red": 0.0, "green": 0.75, "blue": 0.45},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
            })
            _log(f"Created sheet: {sheet_name}")
        else:
            _log(f"Sheet exists: {sheet_name}")


def _ws(wb: gspread.Spreadsheet, name: str) -> gspread.Worksheet:
    return wb.worksheet(name)


def save_profiles(wb: gspread.Spreadsheet, profiles_data: list) -> None:
    """Batch save profile rows. profiles_data: list of (profile_dict, api_used)."""
    if not profiles_data:
        return
    rows = []
    now  = _now()
    for profile, api_used in profiles_data:
        rows.append([
            now,
            profile.get("username", ""),
            profile.get("fullName", ""),
            profile.get("followersCount", 0),
            profile.get("followingCount", 0),
            profile.get("postsCount", 0),
            "Yes" if profile.get("verified") else "No",
            profile.get("biography", "")[:100],
            profile.get("scraped_at", now),
            api_used,
        ])
    _ws(wb, "Creator Profiles").append_rows(rows)
    _log(f"Saved {len(rows)} profiles")


def save_reels(wb: gspread.Spreadsheet, creator_username: str,
               creator_name: str, reels: list, viral_shortcodes: set = None) -> None:
    """Batch save reel rows."""
    if not reels:
        return
    viral_shortcodes = viral_shortcodes or set()
    rows = []
    now  = _now()
    for r in reels:
        posted = r.get("timestamp", "")
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(posted)
            day_of_week = dt.strftime("%A")
            hour_of_day = str(dt.hour)
        except Exception:
            day_of_week = ""
            hour_of_day = ""
        rows.append([
            now,
            creator_username,
            creator_name,
            r.get("shortcode", ""),
            r.get("caption", "")[:100],
            r.get("videoViewCount", 0),
            r.get("likesCount", 0),
            r.get("commentsCount", 0),
            r.get("durationSec", 0),
            posted,
            day_of_week,
            hour_of_day,
            " ".join(r.get("hashtags", [])[:10]),
            r.get("reel_url", ""),
            "YES" if r.get("shortcode") in viral_shortcodes else "NO",
        ])
    _ws(wb, "Reel Stats").append_rows(rows)
    _log(f"Saved {len(rows)} reels for @{creator_username}")


def save_metrics(wb: gspread.Spreadsheet, username: str, metrics: dict) -> None:
    """Save one row of computed creator metrics."""
    best_reel = metrics.get("best_reel") or {}
    row = [
        _now(),
        username,
        metrics.get("followers", 0),
        metrics.get("avg_views", 0),
        metrics.get("avg_likes", 0),
        metrics.get("avg_comments", 0),
        metrics.get("engagement_rate", 0),
        metrics.get("posts_this_week", 0),
        metrics.get("posts_this_month", 0),
        best_reel.get("videoViewCount", 0),
        best_reel.get("reel_url", ""),
        metrics.get("avg_caption_length", 0),
        metrics.get("avg_duration_secs", 0),
        str(metrics.get("best_posting_hour", "")),
        metrics.get("best_posting_day", ""),
        " ".join(metrics.get("most_used_hashtags", [])[:5]),
        metrics.get("posting_frequency_days", 0),
    ]
    _ws(wb, "Creator Metrics").append_row(row)


def save_viral_reel(wb: gspread.Spreadsheet, creator_username: str,
                    creator_name: str, anomaly: dict) -> None:
    """Save one viral reel anomaly row."""
    from processors.hook_extractor import extract_hook_text, classify_hook
    caption = anomaly.get("title", "")
    row = [
        _now(),
        creator_username,
        creator_name,
        anomaly.get("reel_url", ""),
        caption[:80],
        anomaly.get("views", 0),
        anomaly.get("likes", 0),
        anomaly.get("comments", 0),
        anomaly.get("multiplier", 0),
        extract_hook_text(caption),
        classify_hook(caption),
        " ".join(anomaly.get("hashtags", [])[:8]),
        anomaly.get("posted_at", ""),
    ]
    _ws(wb, "Viral Reels").append_row(row)
    _log(f"Saved viral reel: {anomaly.get('reel_url','')[:50]}")


def save_anomaly(wb: gspread.Spreadsheet, username: str,
                 anomaly: dict, alert_sent: bool) -> None:
    """Log one anomaly row."""
    row = [
        _now(),
        username,
        anomaly.get("type", ""),
        anomaly.get("severity", ""),
        anomaly.get("detail", anomaly.get("title", ""))[:200],
        "YES" if alert_sent else "NO",
        "",  # ActionTaken — filled manually
    ]
    _ws(wb, "Anomalies Log").append_row(row)


def save_trending_topics(wb: gspread.Spreadsheet, topics: list) -> None:
    """Batch save trending topic rows."""
    if not topics:
        return
    now  = _now()
    rows = [
        [now, t.get("keyword", ""), t.get("score", 0),
         t.get("type", ""), t.get("direction", ""), t.get("region", "India")]
        for t in topics
    ]
    _ws(wb, "Trending Topics").append_rows(rows)
    _log(f"Saved {len(rows)} trending topics")


def save_content_ideas(wb: gspread.Spreadsheet,
                        hooks: list, ideas: list) -> None:
    """Batch save generated hooks and ideas."""
    rows = []
    date = datetime.now().strftime("%Y-%m-%d")
    for h in hooks:
        rows.append([
            date,
            h.get("hook", ""),
            h.get("pattern", ""),
            h.get("score", 0),
            "",  # IdeaTitle — hook row
            "",  # Urgency
            "", "", "", "", "",
            "",
            "Pending",
        ])
    for idea in ideas:
        outline = idea.get("script_outline", {})
        rows.append([
            date,
            idea.get("hook", ""),
            "",
            "",
            idea.get("title", ""),
            idea.get("urgency", ""),
            idea.get("estimated_views", ""),
            idea.get("why_now", ""),
            idea.get("niche_angle", ""),
            idea.get("best_day", ""),
            idea.get("best_time", ""),
            " ".join(idea.get("hashtags", [])[:8]),
            "Pending",
        ])
    if rows:
        _ws(wb, "Content Ideas").append_rows(rows)
        _log(f"Saved {len(hooks)} hooks + {len(ideas)} ideas")


def save_weekly_report(wb: gspread.Spreadsheet, report: dict) -> None:
    """Save one weekly report summary row."""
    row = [
        report.get("week_start", ""),
        report.get("week_end", ""),
        report.get("creators_tracked", 0),
        report.get("total_viral_spikes", 0),
        report.get("total_anomalies", 0),
        report.get("top_creator", ""),
        report.get("top_topic", ""),
        report.get("ideas_generated", 0),
        report.get("summary", "")[:500],
    ]
    _ws(wb, "Weekly Reports").append_row(row)
    _log("Saved weekly report")


def get_creator_last_metrics(wb: gspread.Spreadsheet, username: str) -> dict | None:
    """Return most recent metrics row for a creator as dict."""
    rows = _ws(wb, "Creator Metrics").get_all_records()
    matches = [r for r in rows if r.get("Username") == username]
    return matches[-1] if matches else None


def get_creator_history(wb: gspread.Spreadsheet,
                         username: str, days: int = 30) -> list:
    """Return last N days of metric rows for a creator."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows   = _ws(wb, "Creator Metrics").get_all_records()
    return [
        r for r in rows
        if r.get("Username") == username and str(r.get("Timestamp", "")) >= cutoff
    ]


def get_all_viral_reels(wb: gspread.Spreadsheet, days: int = 7) -> list:
    """Return viral reels from last N days."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    rows   = _ws(wb, "Viral Reels").get_all_records()
    return [r for r in rows if str(r.get("Timestamp", "")) >= cutoff]


def get_recent_trends(wb: gspread.Spreadsheet, hours: int = 24) -> list:
    """Return trending topics from last N hours."""
    cutoff = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M")
    rows   = _ws(wb, "Trending Topics").get_all_records()
    return [r for r in rows if str(r.get("Timestamp", "")) >= cutoff]
