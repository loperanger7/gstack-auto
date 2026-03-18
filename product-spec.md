gstack Twitter Auto-Reply System

A semi-autonomous system that monitors Twitter/X for mentions of gstack, drafts contextual reply variants using Claude, and lets a human approve or edit before sending. Deployed to Fly.io. The goal: spend 2 minutes a day and maintain an active, authentic Twitter presence for gstack.

Customer Story

I maintain gstack-auto (https://github.com/loperanger7/gstack-auto), built on Garry Tan’s gstack. People mention gstack on Twitter — asking what it is, praising it, comparing tools. I want to reply to those tweets with helpful, contextual responses that link back to gstack-auto. But I don’t want to manually search Twitter all day, and I don’t want to send robotic spam. I want a system that finds the tweets, drafts good replies, and lets me approve them with one tap.

How It Works

The Core Loop (runs every 15 minutes)
Search Twitter for mentions of gstack using expanded queries: “gstack”, “g-stack”, “garry tan gstack”, “@garrytan gstack”, and related phrases
Deduplicate against tweets already seen (by tweet ID in the database)
Check cooldown — skip if we’ve already replied to this author in the past 7 days
Fetch the full thread for each new tweet (up to 10 parent tweets for context)
Draft 2-3 reply variants using Claude Sonnet 4.6:
Read the tweet + thread context
Classify sentiment (praise, question, criticism, neutral mention)
Generate variants with different tones/approaches
Each variant must be ≤280 characters and include a natural mention of gstack-auto where appropriate
Rank tweets by social reach (author’s follower count, descending)
Store in the pending queue for human review
Send a hot-tweet email alert if any tweet author has 50K+ followers
The Approval UI (web dashboard on Fly.io)
The human opens the dashboard, sees pending tweets ranked by reach, picks the best variant (or edits one), chooses a send window, and approves. That’s it.

Reply Scheduling
Approved replies don’t send immediately. They queue into the next available send window:

Morning: 9–11am ET
Lunch: 12–2pm ET
Evening: 5–7pm ET
A background job checks the send queue every minute and posts replies whose window has arrived.

Engagement Tracking
After a reply is sent, the system checks back at 24 hours and 72 hours to record likes and retweets. This data feeds the stats page and will eventually power reply learning (which variant styles perform best).

Weekly Digest Email
Every Monday, send a summary email: tweets found that week, replies sent, engagement metrics (total likes/retweets on replies), top-performing replies, and any errors encountered.

What the User Sees

Dashboard (/dashboard)
Auth: HTTP Basic Auth on first visit. Sets a signed cookie (30-day TTL) so you don’t re-auth on subsequent visits.
Pending queue: Each tweet shows: author name, follower count, tweet text, thread summary, sentiment tag (praise/question/criticism/neutral)
Reply variants: 2-3 draft variants per tweet, each with a character count
Actions per tweet: Pick a variant and approve, edit a variant then approve, or skip
Send window selector: When approving, choose which send window (next morning/lunch/evening)
Sorted by reach: Highest follower count first
Stats Page (/stats)
Cycle history: when each monitor cycle ran, tweets found, drafts created, errors
Reply success rate: approved vs. skipped vs. stale (target tweet deleted)
Engagement metrics: total likes/retweets on sent replies, broken down by variant
Send window performance: which time slots get the most engagement
Health Endpoint (/health)
No auth required
Returns: last successful cycle time, pending queue depth, database size, last error (if any)
Architecture

Tech Stack
Python 3.12 with FastAPI
SQLite with WAL mode on a Fly.io persistent volume
APScheduler for scheduled jobs (monitor every 15m, send queue every 1m, digest weekly)
httpx (async) for Twitter API calls
anthropic SDK for Claude Sonnet 4.6 drafting
smtplib for Gmail SMTP alerts and digest
itsdangerous for signed session cookies
Jinja2 templates (built into FastAPI)
respx + unittest.mock for testing
Database Schema (6 tables)
tweets: id, author_id, author_name, follower_count, text, thread_json, sentiment, found_at, status (pending/replied/skipped/stale)
variants: id, tweet_id, draft_text, variant_label (A/B/C), chosen (bool)
replies: id, variant_id, sent_at, scheduled_for, send_window, twitter_reply_id
cooldowns: author_id, last_replied_at
engagement: reply_id, likes, retweets, checked_at
cycles: id, started_at, completed_at, tweets_found, drafts_created, errors
Key Design Decisions
All SQL in db.py as named functions — the rest of the app never writes raw SQL
Async pipeline with semaphore(10) — thread fetches and Claude calls run concurrently but capped at 10 to respect Twitter rate limits
Proactive rate limit budget tracking — track API calls per 15-min window, stop before hitting Twitter’s 60-request limit
XML-delimited tweet content in Claude prompts — prevents prompt injection from malicious tweet text
Graceful SIGTERM handling — finish current operation before exiting during deploys
Two templates: dashboard.html (interactive approval queue) and stats.html (read-only analytics)
External APIs
Twitter/X API v2 (Basic tier, $100/month) — search tweets, fetch threads, post replies, check engagement
Claude API (Sonnet 4.6) — draft reply variants, ~$0.003 per draft
Gmail SMTP — hot-tweet alerts and weekly digest emails
Deployment

Deploy to Fly.io:

Single instance (no HA needed for single-user system)
Persistent volume for SQLite database
Secrets via fly secrets set for all API keys and passwords
Dockerfile-based deployment
Environment Variables
TWITTER_API_KEY — Twitter/X API key
TWITTER_API_SECRET — Twitter/X API secret
TWITTER_ACCESS_TOKEN — Twitter/X access token
TWITTER_ACCESS_TOKEN_SECRET — Twitter/X access token secret
ANTHROPIC_API_KEY — Claude API key
GMAIL_ADDRESS — Gmail address for sending alerts
GMAIL_APP_PASSWORD — Gmail app password
ALERT_RECIPIENT_EMAIL — Email to receive alerts and digests
DASHBOARD_USERNAME — HTTP Basic Auth username
DASHBOARD_PASSWORD — HTTP Basic Auth password
AUTH_SECRET_KEY — Secret for signing session cookies
HOT_TWEET_THRESHOLD — Follower count threshold for hot-tweet alerts (default: 50000)
COOLDOWN_DAYS — Days before replying to the same author again (default: 7)
Error Handling

Every external call is wrapped with explicit error handling:

Twitter API timeout → retry 2x with backoff, then skip cycle
Twitter 429 rate limit → skip cycle, log, next cycle catches up
Twitter 401 auth failure → log CRITICAL, send email alert
Claude API timeout → retry 2x, fallback to template reply
Claude refusal/empty response → skip tweet
Tweet deleted before reply sent → mark stale in UI
Gmail SMTP failure → log, continue (alerts are supplementary)
SQLite disk full → log CRITICAL, service degrades gracefully
The system is fault-tolerant by nature: if any cycle fails, the next one catches up. No data is lost.

What This Does NOT Do

No multi-platform monitoring (Bluesky, Reddit, HN) — deferred to Phase 2
No reply learning from engagement data — deferred, needs operational data first
No multi-user support — single user system
No mobile app or push notifications — Gmail alerts + responsive dashboard is sufficient
No Slack integration — Gmail only for v1
No automatic sending without human approval — every reply requires explicit approval
Design Direction

Clean, functional dashboard — not flashy, just usable
Mobile-responsive so you can approve replies from your phone
Dark theme preferred
Monospace for tweet text and draft variants
Clear visual hierarchy: highest-reach tweets at top, sentiment tags color-coded
Character count prominently displayed on each variant (green ≤260, yellow 261-270, red 271-280)
