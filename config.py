"""
config.py — All settings, API keys, and creator list for Content Magic.
Loads everything from environment variables. Never hardcode secrets here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API KEYS ────────────────────────────────────────────────────────────────
APIFY_API_TOKEN        = os.getenv("APIFY_API_TOKEN", "")
APIFY_ACTOR_ID         = "apify/instagram-scraper"
APIFY_MONTHLY_LIMIT    = 95          # stop at 95 to leave buffer before hard 100 limit

RAPIDAPI_KEY           = os.getenv("RAPIDAPI_KEY", "")
RAPIDAPI_HOST          = "instagram-scraper-api2.p.rapidapi.com"
RAPIDAPI_BASE_URL      = "https://instagram-scraper-api2.p.rapidapi.com/v1"
RAPIDAPI_MONTHLY_LIMIT = 480         # stop at 480 before hard 500 limit

TELEGRAM_BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID       = os.getenv("TELEGRAM_CHAT_ID", "")

ANTHROPIC_API_KEY      = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL           = "claude-sonnet-4-20250514"

GOOGLE_SHEETS_CREDS    = os.getenv("GOOGLE_SHEETS_CREDS", "credentials.json")
SHEET_NAME             = "ContentMagic_suryanshsk"

# ── SCRAPING SETTINGS ───────────────────────────────────────────────────────
SCRAPE_REELS_COUNT       = 12     # fetch last 12 reels per creator
VIRAL_MULTIPLIER         = 2.0    # 2x avg views = viral spike
TREND_ALERT_SCORE        = 80     # alert if Google Trends score >= this
SCRAPE_INTERVAL_HOURS    = 6      # scrape every 6 hours to save quota
SLEEP_BETWEEN_CREATORS   = 2      # seconds between creator scrapes
QUOTA_FILE               = "quota_tracker.json"

# ── NICHE KEYWORDS ──────────────────────────────────────────────────────────
NICHE_KEYWORDS = [
    "Python tutorial", "AI tools 2025", "machine learning",
    "DevOps tutorial", "coding tricks", "AI agents",
    "web development", "data science", "startup India",
    "tech career India", "DSA interview", "open source AI",
    "LLM tutorial", "prompt engineering", "cloud computing",
]

# ── ALL 73 CREATORS ─────────────────────────────────────────────────────────
CREATORS = [
    {"name": "CodeWithHarry",         "instagram": "codewithharry"},
    {"name": "Ankur Warikoo",         "instagram": "ankurwarikoo"},
    {"name": "Raj Shamani",           "instagram": "rajshamani"},
    {"name": "Nikhil Kamath",         "instagram": "nikhilkamathcio"},
    {"name": "Varun Mayya",           "instagram": "thevarunmayya"},
    {"name": "Aravind Srinivas",      "instagram": "aravindsrinivas"},
    {"name": "Iqlipse Nova",          "instagram": "iqlipse_nova"},
    {"name": "Love Babbar",           "instagram": "lovebabbar1"},
    {"name": "Y Combinator",          "instagram": "ycombinator"},
    {"name": "OpenAI",                "instagram": "openai"},
    {"name": "Google India",          "instagram": "googleindia"},
    {"name": "Piyush Garg",           "instagram": "piyushgarg.official"},
    {"name": "Arsh Goyal",            "instagram": "arshgoyal.ai"},
    {"name": "Shradha Sharma",        "instagram": "shradhasharmayss"},
    {"name": "Perplexity AI",         "instagram": "perplexity"},
    {"name": "100xEngineers",         "instagram": "100xengineers"},
    {"name": "Tech Roast Show",       "instagram": "techroastshow"},
    {"name": "Parth Arora",           "instagram": "dissectthis"},
    {"name": "Dhruv Raina",           "instagram": "dhruvtalkstech"},
    {"name": "Tanmay Bakshi",         "instagram": "tajymany"},
    {"name": "Ruchi Bhatia",          "instagram": "techbyruchi"},
    {"name": "HackwithIndia",         "instagram": "hackwithindia"},
    {"name": "Evolving AI",           "instagram": "evolving.ai"},
    {"name": "Tanmay Tiwari",         "instagram": "takneekitanmay"},
    {"name": "Neeraj Walia EZ",       "instagram": "ezsnippet"},
    {"name": "Warp",                  "instagram": "warpdotdev"},
    {"name": "Replit",                "instagram": "repl.it"},
    {"name": "Vanshika Pandey",       "instagram": "codecrookshanks"},
    {"name": "Anurag Srivastava",     "instagram": "data_with_anurag"},
    {"name": "Md Imran",              "instagram": "mdimran.py"},
    {"name": "H.C. Verma",            "instagram": "hc_verma._"},
    {"name": "Sakshi Tiwari",         "instagram": "girlwhodebugs"},
    {"name": "Jai Chawla",            "instagram": "jaichawla.mp4"},
    {"name": "Paritosh Anand",        "instagram": "iamparitoshanand"},
    {"name": "Jitendra Choudhary",    "instagram": "jituigcoach"},
    {"name": "Nishant Chahar",        "instagram": "nishantchahar.ai"},
    {"name": "Anmol Malik",           "instagram": "agenticanmol"},
    {"name": "Rishika Gupta",         "instagram": "rishikagupta__"},
    {"name": "Tirth Patel",           "instagram": "tirthpatel00"},
    {"name": "Manav Gupta",           "instagram": "tensor._.boy"},
    {"name": "Gayatri Agrawal",       "instagram": "gayatri.tech"},
    {"name": "Priyal",                "instagram": "priyal.py"},
    {"name": "Kabir Arora",           "instagram": "startkabir"},
    {"name": "Archy Gupta",           "instagram": "archy.gupta"},
    {"name": "Manav AI",              "instagram": "manav_ai_"},
    {"name": "Manas Chopra",          "instagram": "themanas.ai"},
    {"name": "Utkarsh Soni",          "instagram": "this_is_sethji"},
    {"name": "Neeraj Walia Build",    "instagram": "buildwithez"},
    {"name": "Hiten Lulla",           "instagram": "hiten.codes"},
    {"name": "Arya Bandhu",           "instagram": "aru_code"},
    {"name": "Sumit Rathore",         "instagram": "sumitinnovate"},
    {"name": "Mann Jadwani",          "instagram": "developer_mannjadwani"},
    {"name": "Vishnu Vijayan",        "instagram": "v.i.s.h.ai"},
    {"name": "Miles AI",              "instagram": "trymiles.ai"},
    {"name": "Sukhad Anand",          "instagram": "techie007.dev"},
    {"name": "Abhay Singh",           "instagram": "abhaysinghlinkedinwala"},
    {"name": "Upasana Singh",         "instagram": "codewithupasana"},
    {"name": "Sumit Rathore Dev",     "instagram": "sumit.rth"},
    {"name": "Dev Taneja",            "instagram": "devtalksbusiness"},
    {"name": "Dev Taneja AI",         "instagram": "unicornin2026"},
    {"name": "Himanshu Gupta",        "instagram": "himanshugupta.io"},
    {"name": "Shaurya Gaikwad",       "instagram": "shauryahelps"},
    {"name": "IndiaAI",               "instagram": "officialindiaai"},
    {"name": "Habiba Bhombal",        "instagram": "pmprohabiba"},
    {"name": "Ritika Singh",          "instagram": "rizdev.in"},
    {"name": "Nishant Unscripted",    "instagram": "unscripted.nishant"},
    {"name": "Hiten Personal",        "instagram": "hiten.lulla"},
    {"name": "Arsh Goyal YT",         "instagram": "arshgoyalyt"},
    {"name": "Vanshika Pandey 2",     "instagram": "missrocknrolla___"},
    {"name": "Prepgenix AI",          "instagram": "prepgenix.ai"},
    {"name": "Sunchit Dudeja",        "instagram": "sunchitdudeja"},
    {"name": "Suryanshsk YOU",        "instagram": "suryanshsk.ai"},
]


def validate_env():
    """Call this at startup. Raises ValueError listing any missing keys."""
    required = {
        "APIFY_API_TOKEN":    APIFY_API_TOKEN,
        "RAPIDAPI_KEY":       RAPIDAPI_KEY,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID":   TELEGRAM_CHAT_ID,
        "ANTHROPIC_API_KEY":  ANTHROPIC_API_KEY,
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            f"Copy .env.example to .env and fill in your keys."
        )
