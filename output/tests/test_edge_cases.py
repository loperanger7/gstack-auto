"""Edge case tests — hostile inputs, boundary conditions, error paths.

Moxie Marlinspike style: every input is hostile, fail closed."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
import aiosqlite
import db
import twitter
import drafter


# --- Database edge cases ---

@pytest_asyncio.fixture
async def conn():
    c = await aiosqlite.connect(":memory:")
    c.row_factory = aiosqlite.Row
    await c.execute("PRAGMA foreign_keys=ON")
    await db.init_db(c)
    # Create a default user for FK constraints
    await db.get_or_create_user(c, "default@test.com", name="Default")
    yield c
    await c.close()


@pytest_asyncio.fixture
async def uid(conn):
    """Return user ID of the default test user."""
    user = await db.get_or_create_user(conn, "default@test.com")
    return user["id"]


class TestHostileDbInputs:
    """Test database layer with hostile/malformed inputs."""

    @pytest.mark.asyncio
    async def test_sql_injection_in_tweet_id(self, conn, uid):
        """SQL injection attempt in tweet_id should be safely parameterized."""
        malicious_id = "'; DROP TABLE tweets; --"
        result = await db.upsert_tweet(
            conn, malicious_id, "a1", "User", 100, "test", user_id=uid
        )
        assert result is True
        # Table should still exist
        cursor = await conn.execute("SELECT COUNT(*) as c FROM tweets")
        row = await cursor.fetchone()
        assert row["c"] == 1

    @pytest.mark.asyncio
    async def test_unicode_in_tweet_text(self, conn, uid):
        """Unicode characters including emoji should be handled."""
        text = "gstack is amazing! \U0001f680\U0001f525 \u2764\ufe0f"
        result = await db.upsert_tweet(conn, "t1", "a1", "User", 100, text, user_id=uid)
        assert result is True
        tweets = await db.get_pending_tweets(conn, user_id=uid)
        assert tweets[0]["text"] == text

    @pytest.mark.asyncio
    async def test_null_bytes_in_text(self, conn, uid):
        """Null bytes in text should not crash the database."""
        text = "hello\x00world"
        result = await db.upsert_tweet(conn, "t2", "a2", "User", 100, text, user_id=uid)
        assert result is True

    @pytest.mark.asyncio
    async def test_empty_string_tweet_id_rejected(self, conn):
        """Empty tweet_id should be rejected."""
        result = await db.upsert_tweet(conn, "", "a1", "User", 100, "test")
        assert result is False

    @pytest.mark.asyncio
    async def test_empty_string_author_id_rejected(self, conn):
        """Empty author_id should be rejected."""
        result = await db.upsert_tweet(conn, "t1", "", "User", 100, "test")
        assert result is False

    @pytest.mark.asyncio
    async def test_whitespace_only_tweet_id(self, conn):
        """Whitespace-only tweet_id should be rejected after stripping."""
        result = await db.upsert_tweet(conn, "   ", "a1", "User", 100, "test")
        assert result is False

    @pytest.mark.asyncio
    async def test_very_long_author_name_truncated(self, conn, uid):
        """Extremely long author name should be truncated."""
        name = "A" * 1000
        result = await db.upsert_tweet(conn, "t3", "a3", name, 100, "test", user_id=uid)
        assert result is True
        cursor = await conn.execute("SELECT author_name FROM tweets WHERE id='t3'")
        row = await cursor.fetchone()
        assert len(row["author_name"]) <= 200

    @pytest.mark.asyncio
    async def test_invalid_sentiment_defaults_to_neutral(self, conn, uid):
        """Invalid sentiment value should default to neutral."""
        result = await db.upsert_tweet(
            conn, "t4", "a4", "User", 100, "test",
            sentiment="malicious_value", user_id=uid
        )
        assert result is True
        cursor = await conn.execute("SELECT sentiment FROM tweets WHERE id='t4'")
        row = await cursor.fetchone()
        assert row["sentiment"] == "neutral"

    @pytest.mark.asyncio
    async def test_duplicate_tweet_id_returns_false(self, conn, uid):
        """Inserting same tweet_id twice should return False on second insert."""
        await db.upsert_tweet(conn, "t5", "a5", "User", 100, "test", user_id=uid)
        result = await db.upsert_tweet(conn, "t5", "a5", "User", 100, "test again", user_id=uid)
        assert result is False

    @pytest.mark.asyncio
    async def test_approve_invalid_window_rejected(self, conn, uid):
        """Approve with invalid send_window should be rejected."""
        await db.upsert_tweet(conn, "t6", "a6", "User", 100, "test", user_id=uid)
        await db.save_variants(conn, "t6", [{"label": "A", "text": "reply"}])
        cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id='t6'")
        vid = (await cursor.fetchone())["id"]
        result = await db.approve_variant(
            conn, "t6", vid, "reply", "2026-01-01T00:00:00", "invalid_window"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_approve_wrong_variant_for_tweet(self, conn, uid):
        """Approve with variant_id that doesn't belong to tweet should fail."""
        await db.upsert_tweet(conn, "t7", "a7", "User", 100, "test", user_id=uid)
        await db.save_variants(conn, "t7", [{"label": "A", "text": "reply"}])
        result = await db.approve_variant(
            conn, "t7", 99999, "reply", "2026-01-01T00:00:00", "morning"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_skip_nonexistent_tweet(self, conn):
        """Skipping a tweet that doesn't exist should return False."""
        result = await db.skip_tweet(conn, "nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_cooldown_with_zero_days(self, conn, uid):
        """Zero cooldown days means always on cooldown after first reply."""
        await db.update_cooldown(conn, "author-1", user_id=uid)
        result = await db.check_cooldown(conn, "author-1", 0, user_id=uid)
        # 0 days means "same day" — should still be on cooldown
        assert result is True

    @pytest.mark.asyncio
    async def test_malformed_thread_json(self, conn, uid):
        """Malformed thread_json should not crash get_pending_tweets."""
        await db.upsert_tweet(
            conn, "t8", "a8", "User", 100, "test",
            thread_json="not valid json {{{",
            user_id=uid,
        )
        tweets = await db.get_pending_tweets(conn, user_id=uid)
        assert len(tweets) == 1
        assert tweets[0]["thread"] == []  # fallback to empty

    @pytest.mark.asyncio
    async def test_engagement_negative_values_clamped(self, conn, uid):
        """Negative engagement values should be clamped to 0."""
        await db.upsert_tweet(conn, "t9", "a9", "User", 100, "test", user_id=uid)
        await db.save_variants(conn, "t9", [{"label": "A", "text": "reply"}])
        cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id='t9'")
        vid = (await cursor.fetchone())["id"]
        await db.approve_variant(
            conn, "t9", vid, "reply", "2026-01-01T00:00:00", "morning"
        )
        cursor = await conn.execute("SELECT id FROM replies WHERE tweet_id='t9'")
        rid = (await cursor.fetchone())["id"]
        await db.upsert_engagement(conn, rid, -10, -5)
        cursor = await conn.execute("SELECT likes, retweets FROM engagement WHERE reply_id=?", (rid,))
        row = await cursor.fetchone()
        assert row["likes"] >= 0
        assert row["retweets"] >= 0


class TestTwitterEdgeCases:
    """Test Twitter module edge cases."""

    def test_rate_budget_starts_at_zero(self):
        twitter.reset_budget()
        assert twitter.budget_usage_pct() == 0.0

    def test_budget_check_resets_after_window(self):
        twitter.reset_budget()
        twitter._rate_budget["window_start"] = 0  # long ago
        assert twitter._check_budget() is True

    def test_percent_encode_special_chars(self):
        assert twitter._percent_encode("hello world") == "hello%20world"
        assert twitter._percent_encode("a&b=c") == "a%26b%3Dc"

    def test_post_reply_rejects_empty_text(self):
        """post_reply should reject empty text synchronously."""
        pass  # covered in test_twitter.py


class TestDrafterEdgeCases:
    """Test drafter module edge cases."""

    def test_xml_escape_handles_all_entities(self):
        result = drafter._xml_escape('<script>alert("xss")</script>')
        assert "<" not in result
        assert ">" not in result
        assert "&lt;" in result

    def test_parse_variants_empty_string(self):
        assert drafter._parse_variants("") == []

    def test_parse_variants_not_json(self):
        assert drafter._parse_variants("not json at all") == []

    def test_parse_variants_json_object_not_array(self):
        assert drafter._parse_variants('{"label":"A","text":"hi"}') == []

    def test_parse_variants_strips_code_fences(self):
        raw = '```json\n[{"label":"A","text":"hello"}]\n```'
        result = drafter._parse_variants(raw)
        assert len(result) == 1
        assert result[0]["text"] == "hello"

    def test_parse_variants_rejects_over_280(self):
        raw = f'[{{"label":"A","text":"{"x" * 300}"}}]'
        result = drafter._parse_variants(raw)
        assert len(result) == 0

    def test_parse_variants_mixed_valid_invalid(self):
        raw = '[{"label":"A","text":"good"},{"label":"B","text":""},{"label":"C","text":"also good"}]'
        result = drafter._parse_variants(raw)
        assert len(result) == 2

    def test_valid_sentiments_frozen(self):
        """VALID_SENTIMENTS should be immutable."""
        assert isinstance(drafter.VALID_SENTIMENTS, frozenset)
        with pytest.raises(AttributeError):
            drafter.VALID_SENTIMENTS.add("evil")
