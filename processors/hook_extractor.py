"""
processors/hook_extractor.py
Extracts and classifies hook patterns from viral Instagram reel captions.
Maps each caption to one of 7 proven viral hook archetypes.
"""

import re

HOOK_PATTERNS = {
    "curiosity_gap":    ["nobody tells you", "secret", "they don't want",
                          "hidden", "untold", "real reason", "don't know",
                          "what they", "truth about"],
    "shock_value":      ["illegal", "impossible", "unbelievable", "shocked",
                          "crazy", "insane", "blew my mind", "jaw drop",
                          "can't believe"],
    "list_format":      [" 5 ", " 7 ", " 10 ", " 3 ", " 8 ", "top ",
                          "best ", "worst ", "reasons", "ways to", "things"],
    "fomo":             ["before it's too late", "2025", "right now",
                          "immediately", "don't miss", "last chance",
                          "stop waiting", "today", "this week"],
    "counterintuitive": ["stop ", "quit ", "don't ", "wrong ", "mistake",
                          "actually ", "contrary", "unpopular opinion",
                          "hot take", "nobody talks"],
    "relatability":     ["every developer", "every coder", "we all",
                          "you're not alone", "same mistake", "been there",
                          "if you're a", "most developers", "most people"],
    "story":            ["i was ", "i built", "i quit", "i failed",
                          "my journey", "how i ", "i went from",
                          "i spent", "after i"],
}


def classify_hook(caption: str) -> str:
    """
    Match first 150 chars of caption against HOOK_PATTERNS.
    Returns pattern name or 'other'.
    """
    if not caption:
        return "other"
    sample = caption[:150].lower()
    for pattern_name, keywords in HOOK_PATTERNS.items():
        if any(kw in sample for kw in keywords):
            return pattern_name
    return "other"


def extract_hook_text(caption: str, max_chars: int = 120) -> str:
    """
    Extract the hook — first meaningful sentence stripped of hashtags/mentions.
    """
    if not caption:
        return ""
    # Remove hashtags and mentions for clean hook
    clean = re.sub(r"[#@]\w+", "", caption).strip()
    clean = re.sub(r"\s+", " ", clean)
    # Cut at first sentence boundary
    for sep in ["\n", ".", "!", "?"]:
        idx = clean.find(sep)
        if 0 < idx <= max_chars:
            return clean[:idx].strip()
    return clean[:max_chars].strip()


def analyze_viral_hooks(viral_reels: list) -> list:
    """
    Analyse a list of viral reel dicts (each must have caption, videoViewCount,
    likesCount, commentsCount, reel_url, creator_name).
    Returns sorted list of hook analysis dicts, highest views first.
    """
    results = []
    for reel in viral_reels:
        caption      = reel.get("caption", "") or ""
        hook_text    = extract_hook_text(caption)
        hook_pattern = classify_hook(caption)
        if not hook_text:
            continue
        results.append({
            "hook_text":    hook_text,
            "pattern":      hook_pattern,
            "views":        reel.get("videoViewCount", 0),
            "likes":        reel.get("likesCount", 0),
            "comments":     reel.get("commentsCount", 0),
            "engagement":   reel.get("likesCount", 0) + reel.get("commentsCount", 0),
            "reel_url":     reel.get("reel_url", ""),
            "creator":      reel.get("creator_name", ""),
            "hashtags":     reel.get("hashtags", []),
        })
    return sorted(results, key=lambda x: x["views"], reverse=True)
