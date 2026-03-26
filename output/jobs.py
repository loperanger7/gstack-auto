"""Scheduled jobs — monitor, send, engagement, digest, email alerts.
Extracted from app.py for testability and single-responsibility."""

import asyncio
import json
import logging
import os
import smtplib
from email.mime.text import MIMEText

import anthropic
import httpx

import db
import drafter
import twitter

log = logging.getLogger(__name__)


def _get_app():
    """Import app module. Deferred to avoid circular imports."""
    import app as app_module
    return app_module


def _is_in_send_window(window_name: str) -> bool:
    """Delegate to app module's send window check."""
    return _get_app()._is_in_send_window(window_name)


# --- Email (fire-and-forget) ---

def _send_email(subject: str, body: str) -> None:
    """Send email via Gmail SMTP. Catches all errors internally."""
    addr = os.environ.get("GMAIL_ADDRESS", "")
    pwd = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("ALERT_RECIPIENT_EMAIL", addr)
    if not addr or not pwd:
        log.info("Email not configured, skipping: %s", subject)
        return
    try:
        msg = MIMEText(body, "plain")
        msg["Subject"] = subject
        msg["From"] = addr
        msg["To"] = recipient
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as s:
            s.starttls()
            s.login(addr, pwd)
            s.send_message(msg)
        log.info("Email sent: %s", subject)
    except Exception as e:
        log.error("Email send failed: %s", e)


# --- Scheduled jobs ---

async def monitor_cycle() -> None:
    """Search Twitter, classify, draft variants, store pending."""
    a = _get_app()
    if a.shutdown_event.is_set():
        return

    log.info("Starting monitor cycle")
    conn = await db.get_connection(a.DB_PATH)
    cycle_id = None
    tweets_found = 0
    drafts_created = 0
    errors_list = []

    try:
        cycle_id = await db.start_cycle(conn)

        async with httpx.AsyncClient() as http_client:
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            if not api_key:
                log.warning("ANTHROPIC_API_KEY not set, skipping drafting")
                return
            claude_client = anthropic.AsyncAnthropic(api_key=api_key)

            mentions = await twitter.search_mentions(http_client)
            tweets_found = len(mentions)

            for mention in mentions:
                if a.shutdown_event.is_set():
                    break

                inserted = await db.upsert_tweet(
                    conn,
                    tweet_id=mention["id"],
                    author_id=mention["author_id"],
                    author_name=mention.get("author_name", ""),
                    follower_count=mention.get("follower_count", 0),
                    text=mention["text"],
                )
                if not inserted:
                    continue

                if await db.check_cooldown(conn, mention["author_id"], a.COOLDOWN_DAYS):
                    log.info("Skipping %s — author on cooldown", mention["id"])
                    continue

                thread = []
                conv_id = mention.get("conversation_id", mention["id"])
                if conv_id:
                    thread = await twitter.fetch_thread(http_client, conv_id)

                thread_json = json.dumps(
                    [{"text": t.get("text", "")} for t in thread] if thread else []
                )
                await conn.execute(
                    "UPDATE tweets SET thread_json = ? WHERE id = ?",
                    (thread_json, mention["id"]),
                )
                await conn.commit()

                sentiment = await drafter.classify_sentiment(claude_client, mention["text"])
                await conn.execute(
                    "UPDATE tweets SET sentiment = ? WHERE id = ?",
                    (sentiment, mention["id"]),
                )
                await conn.commit()

                variants = await drafter.draft_variants(
                    claude_client,
                    tweet_text=mention["text"],
                    author_name=mention.get("author_name", ""),
                    author_username=mention.get("author_username", ""),
                    sentiment=sentiment,
                    thread=thread,
                )
                if variants:
                    count = await db.save_variants(conn, mention["id"], variants)
                    drafts_created += count
                    log.info("Drafted %d variants for tweet %s", count, mention["id"])

                    follower_count = mention.get("follower_count", 0)
                    if isinstance(follower_count, int) and follower_count >= a.HOT_TWEET_THRESHOLD:
                        _send_email(
                            f"HOT TWEET: {mention.get('author_name', '?')} ({follower_count:,} followers)",
                            f"Tweet: {mention['text']}\n\nAuthor: {mention.get('author_name', '')}\n"
                            f"Followers: {follower_count:,}\nID: {mention['id']}",
                        )
                else:
                    log.warning("No variants for tweet %s", mention["id"])

    except twitter.RateLimitError:
        errors_list.append("Rate limit hit")
        log.warning("Rate limit — skipping rest of cycle")
    except twitter.TwitterAuthError:
        errors_list.append("Auth failed")
        log.critical("Twitter auth failed — check credentials")
        _send_email("CRITICAL: Twitter Auth Failed", "Twitter 401. Check API credentials.")
    except Exception as e:
        errors_list.append(str(e)[:200])
        log.error("Monitor cycle error: %s", e, exc_info=True)
    finally:
        if cycle_id is not None:
            await db.end_cycle(
                conn, cycle_id, tweets_found, drafts_created,
                "; ".join(errors_list),
            )
        await conn.close()

    log.info("Monitor cycle done: %d found, %d drafted", tweets_found, drafts_created)


async def send_approved_replies() -> None:
    """Post approved replies whose send window is active."""
    a = _get_app()
    if a.shutdown_event.is_set():
        return

    conn = await db.get_connection(a.DB_PATH)
    try:
        queue = await db.get_send_queue(conn)
        if not queue:
            return

        async with httpx.AsyncClient() as http_client:
            for item in queue:
                if a.shutdown_event.is_set():
                    break

                # Send if ANY window is active. scheduled_for already
                # gates first-eligible time; after that, don't require
                # exact window match or stale replies never send.
                if not any(_is_in_send_window(w) for w in a.VALID_SEND_WINDOWS):
                    continue

                try:
                    reply_id = await twitter.post_reply(
                        http_client, item["tweet_id"], item["reply_text"]
                    )
                    await db.mark_sent(conn, item["reply_id"], reply_id)
                    await db.update_cooldown(conn, item["author_id"])
                    log.info("Sent reply %s to tweet %s", reply_id, item["tweet_id"])
                    await asyncio.sleep(10)
                except twitter.TweetDeletedError:
                    await db.mark_stale(conn, item["tweet_id"])
                    log.warning("Tweet %s deleted, marked stale", item["tweet_id"])
                except twitter.RateLimitError:
                    log.warning("Rate limited during send — will retry next cycle")
                    break
                except Exception as e:
                    log.error("Send failed for tweet %s: %s", item["tweet_id"], e)
    finally:
        await conn.close()


async def check_engagement() -> None:
    """Check engagement on replies sent ~24h and ~72h ago."""
    a = _get_app()
    if a.shutdown_event.is_set():
        return

    conn = await db.get_connection(a.DB_PATH)
    try:
        async with httpx.AsyncClient() as http_client:
            for hours in (24, 72):
                replies = await db.get_replies_needing_engagement_check(conn, hours)
                for r in replies:
                    if not r.get("twitter_reply_id"):
                        continue
                    try:
                        eng = await twitter.get_tweet_engagement(
                            http_client, r["twitter_reply_id"]
                        )
                        if not eng.get("deleted") and not eng.get("error"):
                            await db.upsert_engagement(
                                conn, r["reply_id"], eng["likes"], eng["retweets"]
                            )
                    except Exception as e:
                        log.warning("Engagement check failed for reply %s: %s", r["reply_id"], e)
    finally:
        await conn.close()


async def weekly_digest() -> None:
    """Send weekly digest email every Monday."""
    a = _get_app()
    if a.shutdown_event.is_set():
        return

    conn = await db.get_connection(a.DB_PATH)
    try:
        data = await db.get_weekly_digest(conn)
        body = (
            f"gstack Twitter Auto-Reply — Weekly Digest\n"
            f"{'=' * 45}\n\n"
            f"Tweets found: {data['tweets_found']}\n"
            f"Replies sent: {data['replies_sent']}\n"
            f"Total likes: {data['total_likes']}\n"
            f"Total retweets: {data['total_retweets']}\n"
            f"Error cycles: {data['error_cycles']}\n\n"
        )
        if data["top_replies"]:
            body += "Top Replies:\n"
            for r in data["top_replies"]:
                body += (
                    f"  - To @{r['author_name']} ({r['follower_count']:,} followers): "
                    f"{r['draft_text'][:80]}... "
                    f"[{r['likes']}L {r['retweets']}RT]\n"
                )
        else:
            body += "No replies sent this week.\n"

        _send_email("gstack Weekly Digest", body)
    except Exception as e:
        log.error("Weekly digest failed: %s", e)
    finally:
        await conn.close()
