"""
notifications/telegram_alerts.py
All Telegram alert functions. Uses HTML parse_mode.
Every message is under 4096 chars. Real HTTP calls to Telegram Bot API.
"""

import requests
from datetime import datetime
from collections import Counter
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


BASE_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [Telegram] {msg}")


def _now_ist() -> str:
    return datetime.now().strftime("%d %b %Y, %I:%M %p IST")


def _score_bar(score: int) -> str:
    filled = min(10, score // 10)
    return "█" * filled + "░" * (10 - filled)


def _truncate(text: str, n: int) -> str:
    return text[:n] + "…" if len(text) > n else text


def _send(text: str) -> bool:
    """Send message to Telegram. Returns True if successful."""
    # Telegram hard limit is 4096 chars
    text = text[:4090]
    url  = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        r = requests.post(url, json=payload, timeout=15)
        if r.status_code == 200 and r.json().get("ok"):
            _log("Message sent ✅")
            return True
        _log(f"Send failed: {r.status_code} {r.text[:100]}")
        return False
    except requests.exceptions.Timeout:
        _log("Send timed out")
        return False
    except Exception as e:
        _log(f"Send error: {e}")
        return False


def test_connection() -> bool:
    msg = (
        "✅ <b>Content Magic is LIVE!</b>\n\n"
        "👤 Tracking <b>73 Instagram creators</b> for @suryanshsk\n"
        "🔍 Apify + RapidAPI fallback active\n"
        "📊 Google Sheets connected\n"
        "🤖 Claude AI ideas: daily 6 AM\n\n"
        f"⏰ Started: {_now_ist()}"
    )
    return _send(msg)


def alert_viral_spike(creator_name: str, username: str, hook: str,
                      views: int, avg_views: int, multiplier: float,
                      reel_url: str, hashtags: list) -> bool:
    top_tags = " ".join(f"#{t}" for t in hashtags[:5]) if hashtags else "—"
    msg = (
        f"🚀 <b>VIRAL SPIKE DETECTED!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{creator_name}</b> (@{username})\n"
        f"🎬 Hook: <i>\"{_truncate(hook, 80)}\"</i>\n"
        f"📈 Views: <b>{views:,}</b> ({multiplier}× their avg!)\n"
        f"📊 Their avg: {avg_views:,} views\n"
        f"🏷 {top_tags}\n"
        f"🔗 {reel_url}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>Post similar content TODAY</b>\n"
        f"⏰ {_now_ist()}"
    )
    return _send(msg)


def alert_trending_topic(keyword: str, score: int,
                          trend_type: str, content_idea: str = "") -> bool:
    bar  = _score_bar(score)
    idea = f"\n💡 Idea: <i>{content_idea}</i>" if content_idea else ""
    msg  = (
        f"📈 <b>TRENDING IN YOUR NICHE!</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏷 <b>{keyword}</b>\n"
        f"📊 Score: {bar} {score}/100\n"
        f"🔍 Type: {trend_type}"
        f"{idea}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ <b>Create content NOW before it peaks!</b>\n"
        f"⏰ {_now_ist()}"
    )
    return _send(msg)


def alert_anomaly(creator_name: str, username: str,
                   anomaly_type: str, detail: str) -> bool:
    emojis = {
        "FOLLOWER_SPIKE":   "📈",
        "ENGAGEMENT_DROP":  "📉",
        "POSTING_SPIKE":    "⚡",
        "POSTING_GAP":      "⏸",
    }
    emoji = emojis.get(anomaly_type, "🔔")
    label = anomaly_type.replace("_", " ").title()
    msg   = (
        f"{emoji} <b>{label}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>{creator_name}</b> (@{username})\n"
        f"📝 {_truncate(detail, 200)}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧠 Analyse and adapt your strategy!\n"
        f"⏰ {_now_ist()}"
    )
    return _send(msg)


def send_daily_ideas(hooks: list, ideas: list,
                      best_time: str = "7–9 PM IST") -> bool:
    urgency_emoji = {"URGENT": "🔴", "HOT": "🟠", "RISING": "🟡", "EVERGREEN": "🟢"}

    hooks_text = ""
    for i, h in enumerate(hooks[:5], 1):
        score = h.get("score", 0)
        stars = "★" * int(score) + "☆" * (10 - int(score))
        hooks_text += f"\n{i}. <b>{_truncate(h.get('hook',''), 80)}</b>\n   {stars[:5]} · {h.get('pattern','')}\n"
    if not hooks_text:
        hooks_text = "\n• No strong hooks available yet (waiting for fresh viral data).\n"

    ideas_text = ""
    for idea in ideas[:5]:
        urg   = idea.get("urgency", "RISING")
        emoji = urgency_emoji.get(urg, "🟡")
        ideas_text += (
            f"\n{emoji} [{urg}] <b>{_truncate(idea.get('title',''), 60)}</b>\n"
            f"   Hook: <i>{_truncate(idea.get('hook',''), 60)}</i>\n"
            f"   📅 {idea.get('best_day','')} {idea.get('best_time','')}\n"
        )
    if not ideas_text:
        ideas_text = "\n• No content ideas generated yet (next scrape/trends cycle will fill this).\n"

    msg = (
        f"💡 <b>DAILY CONTENT MAGIC — {datetime.now().strftime('%d %b')}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎣 <b>TOP HOOKS TODAY:</b>{hooks_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚀 <b>CONTENT IDEAS:</b>{ideas_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ Best time to post: <b>{best_time}</b>\n"
        f"🎯 Remember: nail the first 2 seconds!"
    )
    return _send(msg)


def send_weekly_report(report: dict) -> bool:
    top_creators = report.get("top_viral_creators", [])[:3]
    top_topics   = report.get("top_topics", [])[:5]
    action_plan  = report.get("action_plan", [])[:3]

    creators_text = ""
    for i, c in enumerate(top_creators, 1):
        creators_text += f"\n  {i}. <b>{c.get('name','')}</b> — {c.get('avg_views',0):,} avg views"

    topics_text = ""
    for t in top_topics:
        bar = _score_bar(int(t.get("score", 0)))
        topics_text += f"\n  • <b>{t.get('keyword','')}</b> {bar}"

    plan_text = ""
    for i, p in enumerate(action_plan, 1):
        plan_text += f"\n  {i}. {p}"

    msg = (
        f"📋 <b>WEEKLY CONTENT MAGIC REPORT</b>\n"
        f"📅 {report.get('week_start','')} → {report.get('week_end','')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Creators tracked: <b>{report.get('creators_tracked', 73)}</b>\n"
        f"🚀 Viral spikes: <b>{report.get('total_viral_spikes', 0)}</b>\n"
        f"🔔 Anomalies: <b>{report.get('total_anomalies', 0)}</b>\n"
        f"💡 Ideas generated: <b>{report.get('ideas_generated', 0)}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 <b>TOP VIRAL CREATORS:</b>{creators_text or ' None yet'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📈 <b>TOP TRENDING TOPICS:</b>{topics_text or ' None yet'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 <b>THIS WEEK'S ACTION PLAN:</b>{plan_text or ' Check your trends!'}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚡ Content Magic · @suryanshsk · {_now_ist()}"
    )
    return _send(msg)


def send_hourly_creator_digest(creator_stats: list,
                               chunk_size: int = 10,
                               interval_hours: int = 1,
                               total_creators: int | None = None,
                               failed_count: int = 0,
                               partial_count: int = 0,
                               failure_reasons: list[str] | None = None) -> bool:
    """
    Send hourly digest for all creators in chunked Telegram messages.
    creator_stats item fields expected:
      name, username, followers, reels_count, avg_views, avg_likes,
      avg_comments, engagement_rate, best_views, api_used
    """
    if not creator_stats:
        total_configured = int(total_creators or 0)
        reason_text = ""
        reasons = [str(x).strip() for x in (failure_reasons or []) if str(x).strip()]
        if reasons:
            top = Counter(reasons).most_common(5)
            parts = [f"{_truncate(r, 36)} ({n})" for r, n in top]
            reason_text = "\nTopFailReasons: " + " | ".join(parts)
        summary = ""
        if total_configured:
            success_count = max(0, total_configured - int(partial_count) - int(failed_count))
            summary = (
                f"\nSummary: {total_configured} total | {success_count} success | "
                f"{int(partial_count)} partial | {int(failed_count)} failed"
                f"{reason_text}"
            )
        return _send(
            f"<b>HOURLY CREATOR DIGEST</b>\n"
            f"No creator data available this cycle."
            f"{summary}\n"
            f"Time: {_now_ist()}"
        )

    total = len(creator_stats)
    total_configured = int(total_creators or total)
    chunk_size = max(1, int(chunk_size or 10))
    chunks = [creator_stats[i:i + chunk_size] for i in range(0, total, chunk_size)]

    reason_text = ""
    reasons = [str(x).strip() for x in (failure_reasons or []) if str(x).strip()]
    if reasons:
        top = Counter(reasons).most_common(5)
        parts = [f"{_truncate(r, 36)} ({n})" for r, n in top]
        reason_text = "\nTopFailReasons: " + " | ".join(parts)

    ok_all = True
    for idx, chunk in enumerate(chunks, 1):
        lines = []
        for i, c in enumerate(chunk, 1):
            reel_lines = []
            for j, r in enumerate(c.get("reel_details", []), 1):
                posted_at = str(r.get("posted_at", ""))[:19].replace("T", " ")
                shares = r.get("shares", "N/A")
                status = r.get("performance_status", "Average")
                reel_lines.append(
                    f"      {j}) Topic: <i>{_truncate(str(r.get('topic','No topic')), 80)}</i>\n"
                    f"         PostedAt: {posted_at or 'N/A'} | AgeHours: {r.get('age_hours', 0)}\n"
                    f"         Views: {int(r.get('views',0)):,} | Likes: {int(r.get('likes',0)):,} | "
                    f"Comments: {int(r.get('comments',0)):,} | Shares: {shares}\n"
                    f"         ViewsPerHour: {int(r.get('views_per_hour',0)):,} | "
                    f"LikesPerHour: {int(r.get('likes_per_hour',0)):,} | "
                    f"CommentsPerHour: {int(r.get('comments_per_hour',0)):,}\n"
                    f"         Status: <b>{status}</b>\n"
                    f"         Link: {r.get('url','')}"
                )
            reels_block = "\n" + "\n".join(reel_lines) if reel_lines else "\n      No recent reels found"

            lines.append(
                f"{i}. <b>{c.get('name','')}</b> (@{c.get('username','')})\n"
                f"   Followers: {int(c.get('followers', 0)):,} | ReelsFetched: {int(c.get('reels_count', 0))}\n"
                f"   AvgViews: {int(c.get('avg_views', 0)):,} | AvgLikes: {int(c.get('avg_likes', 0)):,} | "
                f"AvgComments: {int(c.get('avg_comments', 0)):,}\n"
                f"   EngagementRate: {float(c.get('engagement_rate', 0)):.2f}% | BestViews: {int(c.get('best_views', 0)):,}\n"
                f"   DataSource: {c.get('api_used','unknown')}\n"
                f"   RecentReels:{reels_block}"
            )

        body = "\n\n".join(lines)
        summary_line = ""
        if idx == 1:
            success_count = max(0, total_configured - int(partial_count) - int(failed_count))
            summary_line = (
                f"\nSummary: {total_configured} total | {success_count} success | "
                f"{int(partial_count)} partial | {int(failed_count)} failed"
                f"{reason_text}"
            )
        msg = (
            f"<b>HOURLY CREATOR DIGEST</b>\n"
            f"WindowHours: {interval_hours}\n"
            f"CreatorsInRun: {total} | Part: {idx}/{len(chunks)}\n"
            f"{summary_line}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{body}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"Time: {_now_ist()}"
        )
        sent = _send(msg)
        ok_all = ok_all and sent

    return ok_all


def send_hourly_ai_insights(insights: list) -> bool:
    if not insights:
        return True

    lines = []
    for i, x in enumerate(insights, 1):
        ideas = x.get("ideas", [])[:2]
        idea_text = " | ".join(ideas) if ideas else "No idea generated"
        lines.append(
            f"{i}. Creator: <b>{x.get('creator','')}</b>\n"
            f"   Status: {x.get('status','Average')}\n"
            f"   WhatWorked: {x.get('what_worked','N/A')}\n"
            f"   WhatFailed: {x.get('what_failed','N/A')}\n"
            f"   ContentIdeas: {idea_text}"
        )

    body = "\n\n".join(lines)

    msg = (
        f"<b>HOURLY AI PERFORMANCE INSIGHTS</b>\n"
        f"GeneratedFrom: Live creator metrics\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{body}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Time: {_now_ist()}"
    )
    return _send(msg)


def alert_quota_warning(service: str, used: int, limit: int) -> bool:
    pct = round(used / limit * 100)
    msg = (
        f"⚠️ <b>API QUOTA WARNING</b>\n\n"
        f"Service: <b>{service.upper()}</b>\n"
        f"Used: {used}/{limit} calls this month ({pct}%)\n"
        f"{_score_bar(pct)} {pct}%\n\n"
        f"{'🔴 CRITICAL — switching to fallback!' if pct >= 90 else '🟡 Getting close — monitor usage'}\n"
        f"⏰ {_now_ist()}"
    )
    return _send(msg)


def alert_job_failed(job_name: str, error: str) -> bool:
    msg = (
        f"❌ <b>JOB FAILED: {job_name}</b>\n\n"
        f"Error: <code>{_truncate(error, 300)}</code>\n\n"
        f"Check GitHub Actions logs for full traceback.\n"
        f"⏰ {_now_ist()}"
    )
    return _send(msg)
