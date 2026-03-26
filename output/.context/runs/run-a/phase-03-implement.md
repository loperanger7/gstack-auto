# Phase 03: Implementation Log — Run A

## Files Created

### Source (5 files, 1,569 lines)
- `app.py` (529 lines) — FastAPI routes, auth (Basic + signed cookie), scheduler lifecycle, monitor cycle orchestration, send queue, engagement checking, weekly digest, email alerts, SIGTERM handling
- `db.py` (487 lines) — All SQL in named functions. 6 tables (tweets, variants, replies, cooldowns, engagement, cycles). Schema versioning, WAL mode, input validation at every boundary
- `twitter.py` (299 lines) — OAuth 1.0a HMAC-SHA1 signing (hand-rolled, no dependencies). Rate budget tracking (55/60 per 15m window). Search, thread fetch, post reply, engagement fetch. Retry with backoff, fail-closed error handling
- `drafter.py` (160 lines) — Claude Sonnet integration. XML-escaped prompts to prevent injection. Sentiment classification + variant drafting. Validates all variants <= 280 chars. Markdown code fence stripping
- `config.py` (94 lines) — Environment variable loading (linter-generated)

### Templates (2 files, 260 lines)
- `templates/dashboard.html` (188 lines) — Dark theme, mobile-responsive. Tweet cards sorted by reach. Variant radio buttons with color-coded character counts. Edit mode with live counter. Send window picker
- `templates/stats.html` (72 lines) — Stats grid, engagement totals, send window performance, cycle history

### Deployment (3 files)
- `Dockerfile` — python:3.12-slim, single stage
- `fly.toml` — Single instance, persistent volume for SQLite
- `requirements.txt` — 9 runtime deps, 3 test deps

## Tests Written

### 121 tests, all passing

| File | Tests | Coverage |
|------|-------|----------|
| test_all.py | 52 | DB schema, OAuth, auth, send windows, full cycle integration |
| test_app.py | 15 | Route auth, dashboard rendering, approve/skip flow, cookie persistence |
| test_db.py | 20 | Insert, dedup, cooldowns, approval, send queue, mark stale/sent |
| test_drafter.py | 9 | Variant parsing, sentiment, XML escaping, Claude refusal/timeout |
| test_main.py | 10 | Async route tests via httpx ASGI transport |
| test_twitter.py | 15 | Search, thread, post, rate budget, engagement, error handling |
| conftest.py | — | Shared fixtures, env setup, in-memory DB |

## Test Results

```
121 passed, 0 failed, 9 warnings in 2.37s
```

Warnings are Starlette template deprecation (cosmetic, non-blocking).

## Success Criteria Check

1. **Deploy to Fly.io, wait 15 minutes, see real pending tweets** — All code in place. Dockerfile + fly.toml configured. Monitor cycle runs every 15 minutes via APScheduler. Tweets stored in SQLite with variants.
2. **Approve a reply, verify it posts at scheduled time** — Approve route creates reply record with scheduled UTC time. Send queue job runs every minute, posts when window arrives, marks sent.

## Decisions Made

1. **Expanded to 6 tables** (from planned 4) — Linter added `engagement` and `cycles` tables for engagement tracking and cycle history. These enable stats page and weekly digest which were in the original spec.
2. **Added stats page** — `templates/stats.html` with tweet status counts, engagement totals, send window performance, and cycle history.
3. **Per-request DB connections** — Instead of global connection, each route opens/closes its own connection. Safer for concurrent access with WAL mode.
4. **Python 3.9 compatibility** — Added `from __future__ import annotations` for `X | None` union syntax support.
5. **SELECT-before-INSERT for dedup** — `upsert_tweet` checks if tweet exists before inserting (instead of relying on `total_changes` which is cumulative).
6. **Send window enforcement** — Replies only post when current ET time is within the named window (morning 9-11, lunch 12-2, evening 5-7), not just when `scheduled_for` timestamp has passed.
7. **Email alerts** — Gmail SMTP for hot-tweet alerts (50K+ followers) and critical auth failures. Fire-and-forget (catches all errors internally).
8. **Rate budget intelligence** — Reduces query count when budget is at 80%, skips entirely at 95%. Adds `-is:retweet` filter to search queries.
