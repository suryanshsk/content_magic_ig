"""
intelligence/idea_generator.py
Uses Claude API (claude-sonnet-4-20250514) to generate viral hooks and
content ideas based on REAL trending topics and viral reel data.
"""

import json
import re
from datetime import datetime
import anthropic
from config import CLAUDE_MODEL


def _log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [AI] {msg}")


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


SYSTEM_PROMPT = (
    "You are a viral content strategist for Indian tech creators on Instagram Reels. "
    "You specialise in short-form video hooks that drive saves, shares, and follows. "
    "You know the Indian tech creator space deeply — DSA, AI/ML, DevOps, startups. "
    "Always return ONLY valid JSON — no markdown fences, no explanation, no preamble."
)


def _safe_parse(text: str) -> list:
    """Parse JSON from Claude response. Strips markdown fences if present."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ```
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        # Try to extract JSON array with regex
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        _log(f"JSON parse failed. Raw: {text[:200]}")
        return []


def generate_hooks(viral_hooks: list, trending_topics: list) -> list:
    """
    Generate 8 viral Instagram Reel hooks modeled from real viral patterns.
    viral_hooks: list of dicts with hook_text, pattern, views, creator
    trending_topics: list of dicts with keyword, score
    Returns sorted list of hook dicts.
    """
    _log("Generating hooks via Claude API...")

    hook_examples = "\n".join(
        f'- "{h.get("hook_text","")}" [{h.get("pattern","")}] — {h.get("views",0):,} views by @{h.get("creator","")}'
        for h in viral_hooks[:10]
    )
    topic_examples = "\n".join(
        f'- {t.get("keyword","")} (score: {t.get("score",0)}/100)'
        for t in trending_topics[:8]
    )

    prompt = f"""Creator context:
- Handle: @suryanshsk
- Niche: Coder + DevOps Engineer + AI/ML + Startups (India)
- Followers: 12,600 | Goal: 50,000
- Platform: Instagram Reels (vertical short video)

REAL VIRAL HOOKS FROM THEIR NICHE THIS WEEK:
{hook_examples or "No data yet"}

CURRENTLY TRENDING IN INDIA (TECH NICHE):
{topic_examples or "No data yet"}

Generate 8 Instagram Reel hooks. Rules:
1. Under 12 words each
2. Use ONE of: curiosity_gap, shock_value, list_format, fomo, counterintuitive, relatability, story
3. Specific to AI/ML/DevOps/Coding — not generic
4. Natural human voice, NOT corporate or AI-sounding
5. Score each 0.0–10.0 based on viral potential

Return ONLY this JSON array:
[
  {{"hook": "hook text", "pattern": "pattern_name", "score": 9.2, "topic": "related trending topic", "why_viral": "one sentence reason"}}
]"""

    try:
        client  = _client()
        message = client.messages.create(
            model      = CLAUDE_MODEL,
            max_tokens = 1200,
            system     = SYSTEM_PROMPT,
            messages   = [{"role": "user", "content": prompt}],
        )
        hooks = _safe_parse(message.content[0].text)
        hooks = sorted(hooks, key=lambda x: float(x.get("score", 0)), reverse=True)
        _log(f"Generated {len(hooks)} hooks")
        return hooks
    except Exception as e:
        _log(f"Hook generation error: {e}")
        return []


def generate_content_ideas(trends: list, viral_reels: list,
                            top_creators_metrics: list) -> list:
    """
    Generate 6 content ideas with urgency labels and full script outlines.
    Returns list of idea dicts.
    """
    _log("Generating content ideas via Claude API...")

    trends_text = "\n".join(
        f'- {t.get("keyword","")} (score: {t.get("score",0)}, {t.get("direction","rising")})'
        for t in trends[:10]
    )
    viral_text = "\n".join(
        f'- @{r.get("CreatorUsername", r.get("creator",""))} | {r.get("Views", r.get("views",0)):,} views | Hook: "{r.get("HookText", r.get("hook_text",""))[:60]}"'
        for r in viral_reels[:8]
    )
    creators_text = "\n".join(
        f'- {c.get("Username","")}: {c.get("AvgViews",0):,} avg views, {c.get("EngagementRate",0)}% eng'
        for c in top_creators_metrics[:5]
    )

    prompt = f"""Creator: @suryanshsk | Niche: Coder + DevOps + AI/ML + Startups (India)
Followers: 12,600 | Goal: 50,000 in 6 months | Platform: Instagram Reels

REAL TRENDING TOPICS RIGHT NOW IN INDIA:
{trends_text or "No trends data"}

VIRAL REELS FROM TRACKED CREATORS THIS WEEK:
{viral_text or "No viral data yet"}

TOP CREATOR BENCHMARKS:
{creators_text or "No benchmark data"}

Generate 6 Instagram Reel content ideas. Each must:
- Exploit a CURRENT trend or viral pattern above
- Fit the unique DevOps + AI/ML combo niche (low competition angle)
- Include a complete 30-second script outline
- Have a realistic urgency: URGENT=post today, HOT=this week, RISING=this month, EVERGREEN=anytime

Return ONLY this JSON array:
[
  {{
    "title": "one sentence reel concept",
    "hook": "exact opening line (under 12 words)",
    "urgency": "URGENT",
    "estimated_views": "50K–200K",
    "why_now": "one sentence reason tied to a real trend above",
    "niche_angle": "what makes this unique for @suryanshsk specifically",
    "best_day": "Monday",
    "best_time": "7–9 PM IST",
    "hashtags": ["#Python", "#AITools", "#DevOps"],
    "script_outline": {{
      "hook_3s": "exact words for first 3 seconds",
      "problem_8s": "one sentence problem statement",
      "value_20s": "the actual insight or demo",
      "cta_30s": "save this + follow for more [topic]"
    }}
  }}
]"""

    try:
        client  = _client()
        message = client.messages.create(
            model      = CLAUDE_MODEL,
            max_tokens = 2000,
            system     = SYSTEM_PROMPT,
            messages   = [{"role": "user", "content": prompt}],
        )
        ideas = _safe_parse(message.content[0].text)
        _log(f"Generated {len(ideas)} content ideas")
        return ideas
    except Exception as e:
        _log(f"Idea generation error: {e}")
        return []


def generate_hourly_ai_insights(creator_digest_rows: list,
                                top_creators: int = 8) -> list:
    """
    Generate concise hourly AI insights from live creator/reel metrics.
    Returns list of dicts: creator, status, what_worked, what_failed, ideas[].
    """
    if not creator_digest_rows:
        return []

    rows = sorted(
        creator_digest_rows,
        key=lambda x: int(x.get("avg_views", 0)),
        reverse=True,
    )[:max(1, top_creators)]

    lines = []
    for r in rows:
        reels = r.get("reel_details", [])[:5]
        reel_lines = []
        for x in reels:
            reel_lines.append(
                f"- topic: {x.get('topic','')} | views: {x.get('views',0)} | "
                f"likes: {x.get('likes',0)} | comments: {x.get('comments',0)} | "
                f"age_h: {x.get('age_hours',0)} | vph: {x.get('views_per_hour',0)} | "
                f"status: {x.get('performance_status','Average')}"
            )
        lines.append(
            f"Creator: {r.get('name','')} (@{r.get('username','')})\n"
            f"followers={r.get('followers',0)}, avg_views={r.get('avg_views',0)}, "
            f"engagement_rate={r.get('engagement_rate',0)}\n"
            f"Reels:\n" + "\n".join(reel_lines)
        )

    prompt = f"""Analyse hourly Instagram performance and suggest quick actions.

Data:
{chr(10).join(lines)}

Return ONLY JSON array:
[
  {{
    "creator": "name",
    "status": "Viral|Above Average|Average|Underperforming",
    "what_worked": "one short sentence",
    "what_failed": "one short sentence",
    "ideas": ["idea 1", "idea 2"]
  }}
]
"""

    try:
        client = _client()
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        data = _safe_parse(message.content[0].text)
        return data if isinstance(data, list) else []
    except Exception as e:
        _log(f"Hourly AI insight error: {e}")
        return []
