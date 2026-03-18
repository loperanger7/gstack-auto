"""Round 2 regression tests — bugs found in prior rounds.

Covers: stats grid orphan fix, CSS duplication elimination,
mobile-responsive breakpoints, input boundary conditions."""

import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import pytest_asyncio
import aiosqlite
import db


# --- Template regression tests ---

class TestTemplateRegression:
    """Verify round-2 template bugs are fixed."""

    def test_stats_uses_base_template(self):
        """Stats template should extend base.html to eliminate CSS duplication."""
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "stats.html")
        with open(path) as f:
            content = f.read()
        assert "{% extends" in content or "{% block" in content, \
            "stats.html should use template inheritance"

    def test_dashboard_uses_base_template(self):
        """Dashboard template should extend base.html to eliminate CSS duplication."""
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")
        with open(path) as f:
            content = f.read()
        assert "{% extends" in content or "{% block" in content, \
            "dashboard.html should use template inheritance"

    def test_base_template_exists(self):
        """A base template should exist for shared CSS/nav."""
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")
        assert os.path.exists(path), "base.html should exist for shared CSS"

    def test_stats_grid_responsive(self):
        """Stats grid should use auto-fit to prevent orphan cards on mobile."""
        path = os.path.join(os.path.dirname(__file__), "..", "templates", "stats.html")
        with open(path) as f:
            content = f.read()
        base_path = os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")
        if os.path.exists(base_path):
            with open(base_path) as f:
                content += f.read()
        assert "auto-fit" in content or "auto-fill" in content, \
            "Stats grid should use auto-fit/auto-fill for responsive layout"

    def test_no_duplicate_nav_css(self):
        """Nav bar CSS should appear in base.html only, not in child templates."""
        base_path = os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")
        if not os.path.exists(base_path):
            pytest.skip("base.html not yet created")
        with open(base_path) as f:
            base_content = f.read()
        assert ".nav-bar" in base_content, "Nav CSS should be in base.html"

        for name in ("dashboard.html", "stats.html"):
            path = os.path.join(os.path.dirname(__file__), "..", "templates", name)
            with open(path) as f:
                child = f.read()
            nav_defs = len(re.findall(r'\.nav-bar\s*\{', child))
            assert nav_defs == 0, f"{name} should not redefine .nav-bar CSS"


class TestMobileResponsiveness:
    """Verify mobile-responsive CSS patterns."""

    def test_touch_targets_44px(self):
        """All interactive elements should have min-height 44px for touch."""
        base_path = os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")
        if not os.path.exists(base_path):
            pytest.skip("base.html not yet created")
        with open(base_path) as f:
            content = f.read()
        dash_path = os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")
        with open(dash_path) as f:
            content += f.read()
        assert "min-height:44px" in content or "min-height: 44px" in content


# --- Input boundary regression tests ---

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


class TestInputBoundaries:
    """Test exact boundary conditions that caused issues in round 2."""

    @pytest.mark.asyncio
    async def test_tweet_text_exactly_280_chars(self, conn, uid):
        """280-char tweet text should be accepted."""
        text = "a" * 280
        result = await db.upsert_tweet(
            conn, "t1", "a1", "User", 100, text, user_id=uid
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_tweet_text_over_10000_truncated(self, conn, uid):
        """Extremely long tweet text should be truncated, not rejected."""
        text = "x" * 20000
        result = await db.upsert_tweet(
            conn, "t2", "a2", "User", 100, text, user_id=uid
        )
        assert result is True
        cursor = await conn.execute("SELECT text FROM tweets WHERE id='t2'")
        row = await cursor.fetchone()
        assert len(row["text"]) <= 10000

    @pytest.mark.asyncio
    async def test_negative_follower_count_clamped(self, conn, uid):
        """Negative follower count should be clamped to 0."""
        result = await db.upsert_tweet(
            conn, "t3", "a3", "User", -500, "hello", user_id=uid
        )
        assert result is True
        cursor = await conn.execute("SELECT follower_count FROM tweets WHERE id='t3'")
        row = await cursor.fetchone()
        assert row["follower_count"] >= 0

    @pytest.mark.asyncio
    async def test_empty_variant_text_rejected(self, conn, uid):
        """Empty variant text should not be saved."""
        await db.upsert_tweet(conn, "t4", "a4", "User", 100, "test", user_id=uid)
        count = await db.save_variants(conn, "t4", [
            {"label": "A", "text": ""},
            {"label": "B", "text": "Valid reply"},
        ])
        assert count == 1  # only the valid one

    @pytest.mark.asyncio
    async def test_variant_over_280_truncated(self, conn, uid):
        """Variant text over 280 chars should be truncated at save."""
        await db.upsert_tweet(conn, "t5", "a5", "User", 100, "test", user_id=uid)
        count = await db.save_variants(conn, "t5", [
            {"label": "A", "text": "x" * 300},
        ])
        assert count == 1
        cursor = await conn.execute(
            "SELECT draft_text FROM variants WHERE tweet_id='t5'"
        )
        row = await cursor.fetchone()
        assert len(row["draft_text"]) <= 280

    @pytest.mark.asyncio
    async def test_approve_exactly_280_chars(self, conn, uid):
        """Approving a 280-char reply should succeed."""
        await db.upsert_tweet(conn, "t6", "a6", "User", 100, "test", user_id=uid)
        await db.save_variants(conn, "t6", [{"label": "A", "text": "short"}])
        cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id='t6'")
        vid = (await cursor.fetchone())["id"]
        reply_text = "a" * 280
        result = await db.approve_variant(
            conn, "t6", vid, reply_text, "2026-01-01T00:00:00", "morning"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_approve_281_chars_rejected(self, conn, uid):
        """Approving a 281-char reply should fail."""
        await db.upsert_tweet(conn, "t7", "a7", "User", 100, "test", user_id=uid)
        await db.save_variants(conn, "t7", [{"label": "A", "text": "short"}])
        cursor = await conn.execute("SELECT id FROM variants WHERE tweet_id='t7'")
        vid = (await cursor.fetchone())["id"]
        reply_text = "a" * 281
        result = await db.approve_variant(
            conn, "t7", vid, reply_text, "2026-01-01T00:00:00", "morning"
        )
        assert result is False
