"""
main.py — Master automation runner for Content Magic (@suryanshsk).
Run once locally OR deploy to GitHub Actions.
Schedules all 4 jobs automatically.

Jobs:
  Every 6h   → Instagram scrape (73 creators) + anomaly alerts
  Every 3h   → Google Trends fetch + high-score alerts
  Daily 6AM  → AI hooks + content ideas → Telegram
  Monday 8AM → Weekly report → Telegram
"""

import os
import sys
import time
import traceback
import schedule
from datetime import datetime, timedelta

# ── Load env vars before any other import ───────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

from config import (
    CREATORS, SCRAPE_REELS_COUNT, validate_env,
    SCRAPE_INTERVAL_HOURS, ENABLE_HOURLY_DIGEST, TELEGRAM_DIGEST_CHUNK_SIZE,
    TELEGRAM_DIGEST_REELS_PER_CREATOR,
    ENABLE_HOURLY_AI_INSIGHTS, HOURLY_AI_TOP_CREATORS,
)
from scrapers.instagram_client import scrape_all_creators
from processors.metrics import calculate_creator_metrics
from processors.anomaly_detector import run_all_checks
from processors.hook_extractor import analyze_viral_hooks
from storage.sheets_db import (
    connect, get_or_create_workbook, setup_all_sheets,
    save_profiles, save_reels, save_metrics,
    save_viral_reel, save_anomaly, save_trending_topics,
    save_content_ideas, get_creator_history, get_all_viral_reels,
    get_recent_trends,
    save_scrape_coverage,
)
from storage.quota_tracker import get_status_string
from notifications.telegram_alerts import (
    test_connection, alert_viral_spike, alert_trending_topic,
    alert_anomaly, send_daily_ideas, alert_job_failed, alert_quota_warning,
    send_hourly_creator_digest, send_hourly_ai_insights,
)
from intelligence.trends_tracker import get_all_trends
from intelligence.idea_generator import (
    generate_hooks, generate_content_ideas, generate_hourly_ai_insights,
)
from reports.weekly_report import run_weekly_report


# ── Global state ─────────────────────────────────────────────────────────────
_wb                  = None   # gspread Spreadsheet — None if Sheets unavailable
_last_scrape_results = []
_last_trends         = []


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def _reel_topic(caption: str) -> str:
    if not caption:
        return "No caption"
    text = str(caption).strip().replace("\n", " ")
    for sep in [".", "!", "?"]:
        idx = text.find(sep)
        if 0 < idx <= 100:
            return text[:idx].strip()
    return text[:100].strip()


def _hours_since(timestamp: str) -> float:
    try:
        dt = datetime.fromisoformat(str(timestamp).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            age = datetime.utcnow() - dt
        else:
            age = datetime.now(dt.tzinfo) - dt
        return max(1.0, age.total_seconds() / 3600)
    except Exception:
        return 1.0


def _performance_status(views: int, avg_views: float) -> str:
    if avg_views <= 0:
        return "Average"
    ratio = views / avg_views
    if ratio >= 2.0:
        return "Viral"
    if ratio >= 1.2:
        return "Above Average"
    if ratio >= 0.8:
        return "Average"
    return "Underperforming"


# ═══════════════════════════════════════════════════════════════════════════
# JOB 1 — Every 6 hours: Instagram scrape + anomaly detection + alerts
# ═══════════════════════════════════════════════════════════════════════════
def run_scrape_job() -> None:
    global _last_scrape_results
    log("=" * 55)
    log("JOB 1 — Instagram Scrape Starting")
    log(get_status_string())
    log("=" * 55)

    try:
        results, failures = scrape_all_creators(
            CREATORS,
            count=SCRAPE_REELS_COUNT,
            include_failures=True,
        )
        _last_scrape_results = results

        profiles_to_save = []
        total_virals     = 0
        total_anomalies  = 0
        creator_digest_rows = []

        for creator_data in results:
            profile  = creator_data["profile"]
            reels    = creator_data["reels"]
            username = profile["username"]
            name     = creator_data.get("creator_name", username)
            api_used = creator_data.get("api_used", "unknown")

            # Compute metrics
            metrics = calculate_creator_metrics(profile, reels)
            reels_sorted = sorted(reels, key=lambda r: str(r.get("timestamp", "")), reverse=True)
            reel_details = []
            for reel in reels_sorted[:max(1, TELEGRAM_DIGEST_REELS_PER_CREATOR)]:
                views = int(reel.get("videoViewCount", 0) or 0)
                likes = int(reel.get("likesCount", 0) or 0)
                comments = int(reel.get("commentsCount", 0) or 0)
                age_hours = round(_hours_since(reel.get("timestamp", "")), 1)
                avg_views = max(1, int(metrics.get("avg_views", 0) or 0))
                reel_details.append({
                    "topic": _reel_topic(reel.get("caption", "")),
                    "posted_at": reel.get("timestamp", ""),
                    "views": views,
                    "likes": likes,
                    "comments": comments,
                    # Share count is not exposed consistently by current providers.
                    "shares": reel.get("shareCount", "N/A"),
                    "age_hours": age_hours,
                    "views_per_hour": int(views / age_hours),
                    "likes_per_hour": int(likes / age_hours),
                    "comments_per_hour": int(comments / age_hours),
                    "performance_status": _performance_status(views, avg_views),
                    "url": reel.get("reel_url", ""),
                })
            creator_digest_rows.append({
                "name": name,
                "username": username,
                "followers": metrics.get("followers", 0),
                "reels_count": len(reels),
                "avg_views": metrics.get("avg_views", 0),
                "avg_likes": metrics.get("avg_likes", 0),
                "avg_comments": metrics.get("avg_comments", 0),
                "engagement_rate": metrics.get("engagement_rate", 0),
                "best_views": (metrics.get("best_reel") or {}).get("videoViewCount", 0),
                "api_used": api_used,
                "reel_details": reel_details,
            })

            # Get historical data for anomaly comparison
            history = []
            if _wb:
                try:
                    history = get_creator_history(_wb, username, days=30)
                except Exception as e:
                    log(f"  History fetch error for @{username}: {e}")

            # Detect anomalies
            anomalies = run_all_checks(creator_data, history, metrics)

            # Collect viral shortcodes for reel marking
            viral_shortcodes = set()
            for a in anomalies:
                if a.get("type") == "VIRAL_SPIKE":
                    viral_shortcodes.add(a.get("shortcode", ""))

            # Save to Sheets (batch)
            if _wb:
                try:
                    profiles_to_save.append((profile, api_used))
                    save_reels(_wb, username, name, reels, viral_shortcodes)
                    save_metrics(_wb, username, metrics)
                except Exception as e:
                    log(f"  Sheets save error for @{username}: {e}")

            # Process each anomaly
            for anomaly in anomalies:
                total_anomalies += 1
                atype = anomaly.get("type", "")

                if atype == "VIRAL_SPIKE":
                    total_virals += 1
                    log(f"  🚀 VIRAL: @{username} — {anomaly['multiplier']}x avg | {anomaly['views']:,} views")

                    sent = alert_viral_spike(
                        creator_name = name,
                        username     = username,
                        hook         = anomaly.get("hook", ""),
                        views        = anomaly["views"],
                        avg_views    = anomaly["avg_views"],
                        multiplier   = anomaly["multiplier"],
                        reel_url     = anomaly.get("reel_url", ""),
                        hashtags     = anomaly.get("hashtags", []),
                    )
                    if _wb:
                        try:
                            save_viral_reel(_wb, username, name, anomaly)
                            save_anomaly(_wb, username, anomaly, alert_sent=sent)
                        except Exception as e:
                            log(f"  Viral save error: {e}")

                elif atype in ("FOLLOWER_SPIKE", "ENGAGEMENT_DROP",
                               "POSTING_SPIKE", "POSTING_GAP"):
                    log(f"  🔔 {atype}: @{username} — {anomaly.get('detail','')[:60]}")
                    sent = alert_anomaly(name, username, atype,
                                         anomaly.get("detail", ""))
                    if _wb:
                        try:
                            save_anomaly(_wb, username, anomaly, alert_sent=sent)
                        except Exception as e:
                            log(f"  Anomaly save error: {e}")

        # Batch save profiles
        if _wb and profiles_to_save:
            try:
                save_profiles(_wb, profiles_to_save)
            except Exception as e:
                log(f"Profile batch save error: {e}")

        # Coverage rows include all configured creators (success + failures).
        if _wb:
            try:
                coverage_rows = []
                for creator_data in results:
                    profile = creator_data.get("profile", {})
                    coverage_rows.append({
                        "creator_name": creator_data.get("creator_name", profile.get("username", "")),
                        "username": profile.get("username", ""),
                        "status": creator_data.get("fetch_status", "SUCCESS"),
                        "api_used": creator_data.get("api_used", "unknown"),
                        "profile_source": creator_data.get("profile_source", creator_data.get("api_used", "unknown")),
                        "reels_source": creator_data.get("reels_source", creator_data.get("api_used", "unknown")),
                        "reels_fetched": len(creator_data.get("reels", [])),
                        "error": creator_data.get("reels_error", ""),
                    })
                coverage_rows.extend(failures)
                save_scrape_coverage(_wb, coverage_rows)
            except Exception as e:
                log(f"Scrape coverage save error: {e}")

        # Hourly digest for all creators (chunked Telegram messages)
        if ENABLE_HOURLY_DIGEST:
            try:
                creator_digest_rows.sort(
                    key=lambda x: int(x.get("avg_views", 0)), reverse=True
                )
                sent = send_hourly_creator_digest(
                    creator_digest_rows,
                    chunk_size=TELEGRAM_DIGEST_CHUNK_SIZE,
                    interval_hours=SCRAPE_INTERVAL_HOURS,
                    total_creators=len(CREATORS),
                    failed_count=len(failures),
                    partial_count=sum(1 for x in results if x.get("fetch_status") == "PARTIAL"),
                    failure_reasons=[x.get("error", "") for x in failures],
                )
                log(f"Hourly digest sent: {sent}")
            except Exception as e:
                log(f"Hourly digest error: {e}")

        if ENABLE_HOURLY_AI_INSIGHTS:
            try:
                ai_insights = generate_hourly_ai_insights(
                    creator_digest_rows,
                    top_creators=HOURLY_AI_TOP_CREATORS,
                )
                ai_sent = send_hourly_ai_insights(ai_insights)
                log(f"Hourly AI insights sent: {ai_sent}")
            except Exception as e:
                log(f"Hourly AI insight error: {e}")

        log(
            f"JOB 1 DONE — {len(results)} success, {len(failures)} failed, "
            f"{total_virals} viral | {total_anomalies} anomalies"
        )
        log(get_status_string())

    except Exception as e:
        log(f"JOB 1 FAILED: {e}")
        traceback.print_exc()
        alert_job_failed("Instagram Scrape", str(e))


# ═══════════════════════════════════════════════════════════════════════════
# JOB 2 — Every 3 hours: Google Trends + alert high-score topics
# ═══════════════════════════════════════════════════════════════════════════
def run_trends_job() -> None:
    global _last_trends
    log("=" * 55)
    log("JOB 2 — Google Trends Starting")
    log("=" * 55)

    try:
        trends      = get_all_trends()
        _last_trends = trends

        if _wb:
            try:
                save_trending_topics(_wb, trends)
            except Exception as e:
                log(f"Trends Sheets save error: {e}")

        # Alert high-scoring topics
        high_score = [t for t in trends if t.get("score", 0) >= 80]
        for topic in high_score[:3]:
            log(f"  📈 TRENDING: {topic['keyword']} (score {topic['score']})")
            alert_trending_topic(
                keyword      = topic["keyword"],
                score        = topic["score"],
                trend_type   = topic.get("type", ""),
                content_idea = f"Make a reel about '{topic['keyword']}' — it's trending now!",
            )

        log(f"JOB 2 DONE — {len(trends)} topics | {len(high_score)} alerts sent")

    except Exception as e:
        log(f"JOB 2 FAILED: {e}")
        traceback.print_exc()
        alert_job_failed("Google Trends", str(e))


# ═══════════════════════════════════════════════════════════════════════════
# JOB 3 — Daily 6 AM IST: AI hooks + ideas → Telegram
# ═══════════════════════════════════════════════════════════════════════════
def run_ideas_job() -> None:
    global _last_trends, _last_scrape_results
    log("=" * 55)
    log("JOB 3 — Daily AI Ideas Starting")
    log("=" * 55)

    try:
        # Ensure ideas job has fresh context on first run of the day.
        if not _last_trends:
            log("Ideas precheck: trends cache empty — running trends job first")
            run_trends_job()

        if not _last_scrape_results:
            log("Ideas precheck: scrape cache empty — running scrape job for seed data")
            run_scrape_job()

        # Pull viral reels from Sheets for context
        viral_reels = []
        top_metrics = []
        if _wb:
            try:
                viral_reels = get_all_viral_reels(_wb, days=7)
                top_metrics = _wb.worksheet("Creator Metrics").get_all_records()
                top_metrics = sorted(
                    top_metrics,
                    key=lambda x: int(x.get("AvgViews", 0)),
                    reverse=True
                )[:5]
            except Exception as e:
                log(f"Sheets read for ideas error: {e}")

        # Analyse viral hooks from this week
        viral_hook_data = analyze_viral_hooks(viral_reels)

        if not viral_hook_data and not _last_trends:
            log("Ideas skipped: no viral/trend context available yet")
            return

        # Generate hooks and ideas
        hooks = generate_hooks(viral_hook_data, _last_trends)
        ideas = generate_content_ideas(_last_trends, viral_reels, top_metrics)

        # Save to Sheets
        if _wb and (hooks or ideas):
            try:
                save_content_ideas(_wb, hooks, ideas)
            except Exception as e:
                log(f"Ideas Sheets save error: {e}")

        # Send to Telegram
        send_daily_ideas(hooks, ideas)

        log(f"JOB 3 DONE — {len(hooks)} hooks | {len(ideas)} ideas generated & sent")

    except Exception as e:
        log(f"JOB 3 FAILED: {e}")
        traceback.print_exc()
        alert_job_failed("Daily Ideas", str(e))


# ═══════════════════════════════════════════════════════════════════════════
# JOB 4 — Every Monday 8 AM IST: Weekly report
# ═══════════════════════════════════════════════════════════════════════════
def run_weekly_report_job() -> None:
    log("=" * 55)
    log("JOB 4 — Weekly Report Starting")
    log("=" * 55)
    try:
        if _wb:
            run_weekly_report(_wb)
        else:
            log("Sheets not connected — skipping weekly report")
    except Exception as e:
        log(f"JOB 4 FAILED: {e}")
        traceback.print_exc()
        alert_job_failed("Weekly Report", str(e))


# ═══════════════════════════════════════════════════════════════════════════
# STARTUP
# ═══════════════════════════════════════════════════════════════════════════
def startup() -> bool:
    global _wb

    print("\n" + "█" * 55)
    print("  ⚡  CONTENT MAGIC — @suryanshsk")
    print("  73 Instagram Creators | Apify + RapidAPI fallback")
    print("  Google Trends | Claude AI | Telegram Alerts")
    print("  Google Sheets Database | GitHub Actions Hosting")
    print("█" * 55 + "\n")

    # Validate all env vars
    log("Validating environment variables...")
    try:
        validate_env()
        log("✅ All env vars present")
    except ValueError as e:
        print(f"\n❌ {e}\n")
        return False

    # Test Telegram
    log("Testing Telegram connection...")
    if not test_connection():
        log("❌ Telegram failed — check BOT_TOKEN and CHAT_ID")
        return False
    log("✅ Telegram connected")

    # Connect Google Sheets
    log("Connecting Google Sheets...")
    try:
        client = connect()
        _wb    = get_or_create_workbook(client)
        setup_all_sheets(_wb)
        log("✅ Google Sheets connected")
    except Exception as e:
        log(f"⚠️  Sheets unavailable ({e}) — alerts will still work")
        _wb = None

    # Show quota status
    log(get_status_string())

    # Run initial jobs immediately
    log("Running initial scrape on startup...")
    run_scrape_job()
    run_trends_job()

    return True


# ═══════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════
def main() -> None:
    if not startup():
        sys.exit(1)

    # Schedule all jobs
    schedule.every(SCRAPE_INTERVAL_HOURS).hours.do(run_scrape_job)
    schedule.every(3).hours.do(run_trends_job)
    schedule.every().day.at("06:00").do(run_ideas_job)
    schedule.every().monday.at("08:00").do(run_weekly_report_job)

    log("\n✅ All jobs scheduled:")
    log(f"   Instagram scrape:  every {SCRAPE_INTERVAL_HOURS} hour(s)")
    log("   Google Trends:     every 3 hours")
    log("   AI ideas:          daily at 6:00 AM")
    log("   Weekly report:     every Monday 8:00 AM")
    log("   Press Ctrl+C to stop\n")

    try:
        while True:
            schedule.run_pending()
            time.sleep(30)
    except KeyboardInterrupt:
        log("\n👋 Content Magic stopped. Goodbye!")


if __name__ == "__main__":
    main()
