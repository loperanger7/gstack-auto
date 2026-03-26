"""Tests for priority tier classification — _classify_tier() and dashboard integration."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio

# Set threshold env vars before importing app/routes
os.environ.setdefault("HOT_TWEET_THRESHOLD", "50000")
os.environ.setdefault("WARM_TWEET_THRESHOLD", "10000")

from routes.dashboard import _classify_tier


class TestClassifyTier:
    """Unit tests for _classify_tier pure function."""

    def test_hot_above_threshold(self):
        assert _classify_tier(100000) == "hot"

    def test_hot_exact_boundary(self):
        """Exactly 50000 should be hot."""
        assert _classify_tier(50000) == "hot"

    def test_warm_above_threshold(self):
        assert _classify_tier(25000) == "warm"

    def test_warm_exact_boundary(self):
        """Exactly 10000 should be warm."""
        assert _classify_tier(10000) == "warm"

    def test_warm_just_below_hot(self):
        """49999 should be warm, not hot."""
        assert _classify_tier(49999) == "warm"

    def test_normal_below_warm(self):
        assert _classify_tier(5000) == "normal"

    def test_normal_just_below_warm(self):
        """9999 should be normal."""
        assert _classify_tier(9999) == "normal"

    def test_normal_zero(self):
        assert _classify_tier(0) == "normal"

    def test_none_returns_normal(self):
        """None follower count treated as normal."""
        assert _classify_tier(None) == "normal"

    def test_negative_returns_normal(self):
        """Negative values treated as normal (falsy int isn't caught by `not`, so check explicitly)."""
        # -1 is truthy in Python, so this tests the int() path
        result = _classify_tier(-1)
        assert result == "normal"

    def test_string_number_returns_correct_tier(self):
        """String that can be cast to int should work."""
        assert _classify_tier("60000") == "hot"
        assert _classify_tier("15000") == "warm"
        assert _classify_tier("500") == "normal"

    def test_invalid_string_returns_normal(self):
        """Non-numeric string should be normal."""
        assert _classify_tier("not-a-number") == "normal"


class TestSQLSortMatchesPythonClassification:
    """Verify that the SQL ORDER BY follower_count DESC matches tier ordering."""

    @pytest_asyncio.fixture
    async def conn_with_tiered_tweets(self):
        import aiosqlite
        import db

        c = await aiosqlite.connect(":memory:")
        c.row_factory = aiosqlite.Row
        await c.execute("PRAGMA foreign_keys=ON")
        await db.init_db(c)

        user = await db.get_or_create_user(c, email="tier@test.com", name="Tier Test")
        uid = user["id"]

        # Insert tweets at various follower counts
        for tid, fc in [("hot1", 80000), ("warm1", 20000), ("normal1", 3000),
                        ("hot2", 50000), ("warm2", 10000), ("normal2", 0)]:
            await db.upsert_tweet(
                c, tweet_id=tid, author_id=f"a-{tid}", author_name=f"Author {tid}",
                follower_count=fc, text=f"Tweet {tid}", user_id=uid,
            )

        yield c, uid
        await c.close()

    @pytest.mark.asyncio
    async def test_sql_order_matches_tier_priority(self, conn_with_tiered_tweets):
        """Tweets ordered by follower_count DESC should produce hot, warm, normal grouping."""
        import db

        conn, uid = conn_with_tiered_tweets
        tweets = await db.get_pending_tweets(conn, user_id=uid)

        tiers = [_classify_tier(t["follower_count"]) for t in tweets]

        # All hot tweets should come before warm, warm before normal
        hot_indices = [i for i, t in enumerate(tiers) if t == "hot"]
        warm_indices = [i for i, t in enumerate(tiers) if t == "warm"]
        normal_indices = [i for i, t in enumerate(tiers) if t == "normal"]

        if hot_indices and warm_indices:
            assert max(hot_indices) < min(warm_indices), "Hot tweets should sort before warm"
        if warm_indices and normal_indices:
            assert max(warm_indices) < min(normal_indices), "Warm tweets should sort before normal"
        if hot_indices and normal_indices:
            assert max(hot_indices) < min(normal_indices), "Hot tweets should sort before normal"
