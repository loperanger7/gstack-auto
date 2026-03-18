# gstack Twitter Auto-Reply System

Semi-autonomous system that monitors Twitter for gstack mentions, drafts reply variants using Claude, and lets you approve before sending. Deployed to Fly.io.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env  # fill in your credentials
```

## Required Environment Variables

```bash
export CONSUMER_KEY="your-twitter-consumer-key"
export CONSUMER_KEY_SECRET="your-twitter-consumer-secret"
export ACCESS_TOKEN="your-twitter-access-token"
export ACCESS_TOKEN_SECRET="your-twitter-access-token-secret"
export ANTHROPIC_API_KEY="your-claude-api-key"
export DASHBOARD_USERNAME="admin"
export DASHBOARD_PASSWORD="your-password"
export AUTH_SECRET_KEY="a-random-secret-for-cookie-signing"
```

Optional:
```bash
export GMAIL_ADDRESS="you@gmail.com"
export GMAIL_APP_PASSWORD="your-app-password"
export ALERT_RECIPIENT_EMAIL="alerts@example.com"
export HOT_TWEET_THRESHOLD="50000"
export COOLDOWN_DAYS="7"
export DB_PATH="data/gstack_replies.db"
```

## Run

```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

Open `http://localhost:8080/dashboard` and log in with your credentials.

## Test

```bash
cd output && python -m pytest tests/ -v
```

## Deploy to Fly.io

```bash
fly launch
fly secrets set CONSUMER_KEY=... CONSUMER_KEY_SECRET=... ACCESS_TOKEN=... ACCESS_TOKEN_SECRET=... ANTHROPIC_API_KEY=... DASHBOARD_USERNAME=... DASHBOARD_PASSWORD=... AUTH_SECRET_KEY=...
fly deploy
```

## Architecture

- `app.py` — FastAPI app, routes, auth, scheduler, email alerts
- `db.py` — SQLite WAL schema and all query functions
- `twitter.py` — Twitter API v2 client with OAuth 1.0a signing
- `drafter.py` — Claude-powered reply drafting with XML-safe prompts
- `config.py` — Environment variable loading and validation
- `templates/dashboard.html` — Approval queue (dark theme, mobile)
- `templates/stats.html` — Engagement metrics and cycle history
