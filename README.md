# ⚡ Content Magic — @suryanshsk
### 73 Instagram Creators · Apify + RapidAPI Fallback · Real Alerts · Production Ready

---

## What this does (for real)

| What | How | Cost |
|------|-----|------|
| Scrapes 73 Instagram creator profiles + reels | Apify (primary) → RapidAPI (fallback) | Free tiers |
| Detects viral spikes (2× avg views) | Python anomaly detector | Free |
| Instant Telegram alert when spike found | Telegram Bot API | Free |
| Tracks follower spikes, engagement drops | Anomaly detector | Free |
| Google Trends for your niche (India) | pytrends library | Free |
| Saves everything to Google Sheets | Google Sheets API | Free |
| Daily AI hooks + content ideas at 6 AM | Claude API | ~₹400/mo |
| Weekly Monday digest report | Claude API + Sheets | Included |
| Runs automatically every hour forever | GitHub Actions | Free |

**Total: ₹0–₹400/month**

---

## Project Structure

```
content_magic_ig/
├── main.py                          ← Master runner (entry point)
├── config.py                        ← All settings + 73 creators
├── requirements.txt
├── .env.example                     ← Copy to .env and fill keys
├── .gitignore
├── quota_tracker.json               ← Auto-created, tracks API usage
│
├── scrapers/
│   ├── apify_scraper.py             ← PRIMARY: Apify Instagram scraper
│   ├── rapidapi_scraper.py          ← FALLBACK: RapidAPI scraper
│   └── instagram_client.py          ← Unified client (auto fallback)
│
├── processors/
│   ├── metrics.py                   ← Compute avg views, engagement, etc.
│   ├── anomaly_detector.py          ← Detect viral spikes, drops, gaps
│   └── hook_extractor.py            ← Classify viral caption patterns
│
├── storage/
│   ├── quota_tracker.py             ← Track Apify/RapidAPI monthly usage
│   └── sheets_db.py                 ← Google Sheets database (8 tabs)
│
├── notifications/
│   └── telegram_alerts.py           ← All Telegram alert functions
│
├── intelligence/
│   ├── trends_tracker.py            ← Google Trends via pytrends (free)
│   └── idea_generator.py            ← Claude API: hooks + ideas
│
├── reports/
│   └── weekly_report.py             ← Monday digest generator
│
└── .github/
    └── workflows/
        └── content_magic.yml        ← GitHub Actions (free hosting)
```

---

## SETUP — 5 steps, ~30 minutes total

---

### STEP 1 — Apify (5 minutes)
*Primary Instagram scraper. Free tier: 100 actor runs/month.*

1. Go to **https://console.apify.com** → Sign up free
2. Click your avatar (top right) → **Settings** → **Integrations**
3. Copy your **Personal API token**
4. Paste into `.env` as `APIFY_API_TOKEN`

---

### STEP 2 — RapidAPI (5 minutes)
*Fallback scraper. Free tier: 500 calls/month.*

1. Go to **https://rapidapi.com** → Sign up free
2. Search: **"Instagram Scraper API2"** (by hemanth.harikrishnan)
3. Click **Subscribe** → choose **Basic (FREE)**
4. Go to the **Endpoints** tab → look at any endpoint
5. On the right panel, copy the value of **`X-RapidAPI-Key`**
6. Paste into `.env` as `RAPIDAPI_KEY`

---

### STEP 3 — Telegram Bot (5 minutes)
*Instant alerts to your phone. Completely free.*

1. Open Telegram → search **@BotFather**
2. Send: `/newbot`
3. Choose a name: `ContentMagic suryanshsk`
4. Choose a username: `contentmagic_suryanshsk_bot`
5. BotFather sends you a **token** → paste as `TELEGRAM_BOT_TOKEN`
6. **Start a chat with your bot** (search the bot username, click Start)
7. Message **@userinfobot** → it replies with your **Chat ID**
8. Paste Chat ID as `TELEGRAM_CHAT_ID`

---

### STEP 4 — Google Sheets (10 minutes)
*Free database. Stores all scraped data permanently.*

1. Go to **https://console.cloud.google.com**
2. Click **Select a project** → **New Project** → name it `ContentMagic`
3. Click **Enable APIs and Services**
   - Search **Google Sheets API** → Enable
   - Search **Google Drive API** → Enable
4. Go to **Credentials** → **Create Credentials** → **Service Account**
   - Name: `content-magic`
   - Click **Create and Continue** → Skip optional fields → **Done**
5. Click the service account you just created → **Keys** tab
6. **Add Key** → **Create new key** → **JSON** → Download
7. Rename the downloaded file to `credentials.json`
8. Put `credentials.json` in the same folder as `main.py`
9. Open the JSON file → find `"client_email"` → copy that email address
10. Go to **https://sheets.google.com** → create a new blank spreadsheet
11. Click **Share** → paste the `client_email` → Editor access → **Done**

The automation will create all 8 tabs automatically on first run.

---

### STEP 5 — Anthropic Claude API (3 minutes)
*For daily hook and idea generation. ~₹400/month for daily use.*

1. Go to **https://console.anthropic.com** → Sign up
2. Go to **API Keys** → **Create Key** → name it `ContentMagic`
3. Copy the key → paste as `ANTHROPIC_API_KEY`

---

### STEP 6 — Create your .env file

```bash
cp .env.example .env
```

Open `.env` and fill in all 5 values:
```
APIFY_API_TOKEN=apify_api_...
RAPIDAPI_KEY=abc123...
TELEGRAM_BOT_TOKEN=1234567890:ABC...
TELEGRAM_CHAT_ID=987654321
ANTHROPIC_API_KEY=sk-ant-...
```

---

### STEP 7 — Test locally first

```bash
# Install dependencies
pip install -r requirements.txt

# Run it — it will test Telegram, connect Sheets, run first scrape
python main.py
```

You should see:
```
✅ All env vars present
✅ Telegram connected
✅ Google Sheets connected
[Starting scrape of 73 creators...]
```
And a Telegram message: **"Content Magic is LIVE!"**

---

### STEP 8 — Push to GitHub (free automated hosting)

```bash
# Create a new PRIVATE repo on github.com named: content-magic

git init
git add .
git commit -m "Content Magic — initial setup"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/content-magic.git
git push -u origin main
```

**Add GitHub Secrets** (so your keys stay private):

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret** for each:

| Secret Name | Value |
|---|---|
| `APIFY_API_TOKEN` | your Apify token |
| `RAPIDAPI_KEY` | your RapidAPI key |
| `TELEGRAM_BOT_TOKEN` | your bot token |
| `TELEGRAM_CHAT_ID` | your chat ID |
| `ANTHROPIC_API_KEY` | your Claude key |
| `GOOGLE_CREDENTIALS_JSON` | paste the **entire contents** of credentials.json |

3. Go to **Actions** tab → you'll see **Content Magic** workflow
4. Click **Run workflow** → **Run workflow** (manual test)
5. Watch it run → check your Telegram for the alert!

---

## What happens automatically after setup

### Every hour:
- Scrapes all 73 Instagram creators (profile + last 12 reels)
- Detects viral spikes, follower spikes, engagement drops, posting gaps
- **Instant Telegram alert** for every viral spike found
- **Hourly Telegram digest** with per-creator metrics (followers, reels, avg views/likes/comments)
- Saves everything to Google Sheets

### Every 3 hours:
- Checks Google Trends for your niche keywords in India
- **Telegram alert** if any topic scores 80+/100

### Daily at 6:00 AM IST:
- Reads real viral data from the week
- Calls Claude API to generate 8 hooks + 6 content ideas
- Sends all ideas to **Telegram** with urgency labels
- Saves to Google Sheets "Content Ideas" tab

### Every Monday at 8:00 AM IST:
- Compiles full week stats from Sheets
- Generates strategy summary via Claude API
- Sends **weekly digest** to Telegram
- 3 specific action items for the week

---

## Your Google Sheet tabs (auto-created)

| Tab | What's stored |
|-----|---------------|
| Creator Profiles | Username, followers, bio, verified status |
| Reel Stats | Every reel — views, likes, comments, duration, posted time |
| Creator Metrics | Avg views, engagement rate, best posting hour/day |
| Viral Reels | All 2×+ spike reels with hook text and pattern |
| Anomalies Log | Every anomaly detected with severity and alert status |
| Trending Topics | Google Trends data updated every 3 hours |
| Content Ideas | Daily AI-generated hooks and ideas |
| Weekly Reports | Monday digests |

---

## API Quota Management

The system tracks usage in `quota_tracker.json` automatically:

- **Apify**: stops at 95/100 runs/month → switches to RapidAPI
- **RapidAPI**: stops at 480/500 calls/month → logs warning, skips creator
- **Monthly reset**: auto-resets on 1st of every month
- **Telegram warning**: sent when either API hits 80% usage

You'll never hit a hard limit unexpectedly.

---

## Troubleshooting

**"Telegram not connected"**
→ Check BOT_TOKEN is correct and you've sent `/start` to the bot

**"Apify returned None for @username"**
→ That creator's account may be private or the username changed
→ System automatically falls back to RapidAPI

**"Sheets not connected"**
→ Check credentials.json exists in the project folder
→ Check you shared the Google Sheet with the `client_email` from the JSON

**"Both APIs quota exhausted"**
→ Wait for monthly reset on 1st, or upgrade one plan
→ System skips those creators gracefully, others still work

**GitHub Actions not running**
→ Go to repo → Actions → Enable workflows (GitHub sometimes disables by default)

---

## Production Runbook (Windows + GitHub)

Use this exact order for a clean production setup.

### 1) Local install and test (Windows PowerShell)

```powershell
cd "c:\Users\admin\OneDrive - MSFT\content_magic_ig"
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m compileall -q .
python main.py
```

If `python main.py` starts and Telegram receives the startup message, local setup is healthy.

### 2) Push to GitHub

```powershell
git init
git add .
git commit -m "Initial Content Magic setup"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/content-magic.git
git push -u origin main
```

### 3) Configure repository secrets

Add these in GitHub: Settings → Secrets and variables → Actions.

- `APIFY_API_TOKEN`
- `RAPIDAPI_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `ANTHROPIC_API_KEY`
- `GOOGLE_CREDENTIALS_JSON` (full JSON content, not path)

### 4) Verify both workflows

- `CI` workflow (`.github/workflows/ci.yml`) runs automatically on `push` and `pull_request`.
- `Content Magic — @suryanshsk` workflow (`.github/workflows/content_magic.yml`) runs on schedule and manual dispatch.

For first production check:

1. Open Actions tab
2. Run `Content Magic — @suryanshsk` with `job = all`
3. Confirm all jobs pass and Telegram alerts arrive
