"""Claude-powered reply drafting with XML-safe prompt construction."""

from __future__ import annotations

import json
import logging
import xml.sax.saxutils

import anthropic

log = logging.getLogger(__name__)

VALID_SENTIMENTS = frozenset({"praise", "question", "criticism", "neutral"})

SENTIMENT_PROMPT = """Classify the sentiment of this tweet about gstack into exactly one category: praise, question, criticism, or neutral.

<tweet_text>{tweet_text}</tweet_text>

Respond with ONLY one word: praise, question, criticism, or neutral."""

DRAFT_PROMPT = """You are helping maintain an authentic Twitter presence for gstack-auto, an open-source project built on Garry Tan's gstack.

A Twitter user posted the following tweet. Draft 2-3 reply variants.

<tweet_author>{author_name} (@{author_username})</tweet_author>
<tweet_text>{tweet_text}</tweet_text>
<tweet_sentiment>{sentiment}</tweet_sentiment>
<thread_context>{thread_context}</thread_context>

Rules:
- Each reply MUST be 280 characters or fewer
- Be helpful and genuine, not promotional or spammy
- If relevant, mention gstack-auto naturally (don't force it)
- Match the tone: supportive for praise, helpful for questions, respectful for criticism, conversational for neutral
- No hashtags, no emojis unless the original tweet uses them

Respond with a JSON array of objects, each with "label" (A, B, or C) and "text" fields. Example:
[{{"label": "A", "text": "Your reply here"}}, {{"label": "B", "text": "Another reply"}}]

Return ONLY the JSON array, nothing else."""


def _xml_escape(text: str) -> str:
    """Escape text for safe embedding in XML-delimited prompts."""
    return xml.sax.saxutils.escape(text)


async def classify_sentiment(client: anthropic.AsyncAnthropic, tweet_text: str) -> str:
    """Classify tweet sentiment. Returns one of: praise, question, criticism, neutral."""
    prompt = SENTIMENT_PROMPT.format(tweet_text=_xml_escape(tweet_text))
    try:
        resp = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        result = resp.content[0].text.strip().lower()
        if result in VALID_SENTIMENTS:
            return result
        log.warning("Unexpected sentiment '%s', defaulting to neutral", result)
        return "neutral"
    except anthropic.APITimeoutError:
        log.warning("Claude timeout during sentiment classification")
        return "neutral"
    except Exception as e:
        log.warning("Sentiment classification failed: %s", e)
        return "neutral"


async def draft_variants(
    client: anthropic.AsyncAnthropic,
    tweet_text: str,
    author_name: str,
    author_username: str,
    sentiment: str,
    thread: list[dict] | None = None,
    retries: int = 2,
) -> list[dict]:
    """Generate 2-3 reply variants. Returns list of {label, text} dicts."""
    thread_context = ""
    if thread:
        thread_lines = []
        for t in thread[:10]:
            thread_lines.append(f"- {_xml_escape(t.get('text', ''))}")
        thread_context = "\n".join(thread_lines)

    prompt = DRAFT_PROMPT.format(
        tweet_text=_xml_escape(tweet_text),
        author_name=_xml_escape(author_name),
        author_username=_xml_escape(author_username),
        sentiment=sentiment,
        thread_context=thread_context or "(no thread context)",
    )

    for attempt in range(retries + 1):
        try:
            resp = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text.strip()
            variants = _parse_variants(raw)
            if variants:
                return variants
            log.warning("No valid variants parsed from Claude response")
            if attempt < retries:
                continue
            return []
        except anthropic.APITimeoutError:
            log.warning("Claude timeout (attempt %d/%d)", attempt + 1, retries + 1)
            if attempt < retries:
                continue
            return []
        except anthropic.APIStatusError as e:
            if "refused" in str(e).lower() or "content" in str(e).lower():
                log.warning("Claude refused to draft for this tweet: %s", e)
                return []
            if attempt < retries:
                continue
            log.error("Claude API error: %s", e)
            return []
        except Exception as e:
            log.error("Unexpected drafting error: %s", e)
            return []


def _parse_variants(raw: str) -> list[dict]:
    """Parse Claude's JSON response into validated variants."""
    try:
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:])
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        data = json.loads(text)
        if not isinstance(data, list):
            return []

        valid = []
        for item in data:
            if not isinstance(item, dict):
                continue
            label = str(item.get("label", "")).strip()
            draft = str(item.get("text", "")).strip()
            if not label or not draft:
                continue
            if len(draft) > 280:
                log.warning("Variant %s exceeds 280 chars (%d), discarding", label, len(draft))
                continue
            valid.append({"label": label, "text": draft})

        return valid
    except (json.JSONDecodeError, TypeError, KeyError) as e:
        log.warning("Failed to parse variants JSON: %s", e)
        return []
