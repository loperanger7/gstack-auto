"""Regression tests for Round 3 — managed_connection, CSP, URL validation, ARIA, UX polish."""

import os
import sys
import pytest
import pytest_asyncio
import aiosqlite

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("AUTH_SECRET_KEY", "test-secret-key-for-signing")
os.environ.setdefault("DB_PATH", ":memory:")
os.environ.setdefault("GOOGLE_CLIENT_ID", "test-google-client-id")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-google-client-secret")
os.environ.setdefault("ADMIN_EMAILS", "admin@test.com")

import db


# --- managed_connection tests ---


class TestManagedConnection:
    """Test the managed_connection context manager."""

    @pytest.mark.asyncio
    async def test_managed_connection_yields_connection(self, tmp_path):
        """managed_connection should yield a usable connection."""
        db_path = str(tmp_path / "test.db")
        async with db.managed_connection(db_path) as conn:
            assert conn is not None
            await db.init_db(conn)
            cursor = await conn.execute("SELECT 1 as val")
            row = await cursor.fetchone()
            assert row[0] == 1

    @pytest.mark.asyncio
    async def test_managed_connection_closes_on_success(self, tmp_path):
        """Connection should be closed after context exits normally."""
        db_path = str(tmp_path / "test.db")
        async with db.managed_connection(db_path) as conn:
            await db.init_db(conn)
        # Connection should be closed — trying to use it should fail or be closed
        # aiosqlite doesn't expose .closed directly, but execute should fail
        with pytest.raises(Exception):
            await conn.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_managed_connection_closes_on_exception(self, tmp_path):
        """Connection should be closed even when an exception occurs."""
        db_path = str(tmp_path / "test.db")
        conn_ref = None
        with pytest.raises(ValueError):
            async with db.managed_connection(db_path) as conn:
                conn_ref = conn
                await db.init_db(conn)
                raise ValueError("test error")
        # Connection should still be closed
        with pytest.raises(Exception):
            await conn_ref.execute("SELECT 1")

    @pytest.mark.asyncio
    async def test_managed_connection_explicit_memory(self):
        """managed_connection with explicit :memory: path should work."""
        async with db.managed_connection(":memory:") as conn:
            assert conn is not None
            await db.init_db(conn)

    @pytest.mark.asyncio
    async def test_managed_connection_wal_mode(self, tmp_path):
        """managed_connection should enable WAL mode."""
        db_path = str(tmp_path / "test.db")
        async with db.managed_connection(db_path) as conn:
            cursor = await conn.execute("PRAGMA journal_mode")
            row = await cursor.fetchone()
            assert row[0] == "wal"

    @pytest.mark.asyncio
    async def test_managed_connection_foreign_keys(self, tmp_path):
        """managed_connection should enable foreign keys."""
        db_path = str(tmp_path / "test.db")
        async with db.managed_connection(db_path) as conn:
            cursor = await conn.execute("PRAGMA foreign_keys")
            row = await cursor.fetchone()
            assert row[0] == 1


# --- URL validation tests ---


class TestURLValidation:
    """Test URL validation in settings and onboarding routes."""

    def test_settings_validate_url_rejects_javascript(self):
        from routes.settings import _validate_url
        assert _validate_url("javascript:alert(1)") == ""

    def test_settings_validate_url_rejects_data(self):
        from routes.settings import _validate_url
        assert _validate_url("data:text/html,<script>alert(1)</script>") == ""

    def test_settings_validate_url_rejects_vbscript(self):
        from routes.settings import _validate_url
        assert _validate_url("vbscript:msgbox") == ""

    def test_settings_validate_url_rejects_file(self):
        from routes.settings import _validate_url
        assert _validate_url("file:///etc/passwd") == ""

    def test_settings_validate_url_accepts_https(self):
        from routes.settings import _validate_url
        assert _validate_url("https://example.com") == "https://example.com"

    def test_settings_validate_url_accepts_http(self):
        from routes.settings import _validate_url
        assert _validate_url("http://example.com") == "http://example.com"

    def test_settings_validate_url_rejects_empty(self):
        from routes.settings import _validate_url
        assert _validate_url("") == ""

    def test_settings_validate_url_rejects_no_scheme(self):
        from routes.settings import _validate_url
        assert _validate_url("example.com") == ""

    def test_settings_validate_url_rejects_no_netloc(self):
        from routes.settings import _validate_url
        assert _validate_url("http://") == ""

    def test_settings_validate_url_truncates_long_url(self):
        from routes.settings import _validate_url
        long_url = "https://example.com/" + "a" * 600
        result = _validate_url(long_url)
        assert len(result) <= 500

    def test_settings_validate_url_strips_whitespace(self):
        from routes.settings import _validate_url
        assert _validate_url("  https://example.com  ") == "https://example.com"

    def test_onboarding_validate_url_rejects_javascript(self):
        from routes.onboarding import _validate_url
        assert _validate_url("javascript:alert(1)") == ""

    def test_onboarding_validate_url_rejects_data(self):
        from routes.onboarding import _validate_url
        assert _validate_url("data:text/html,bad") == ""

    def test_onboarding_validate_url_accepts_https(self):
        from routes.onboarding import _validate_url
        assert _validate_url("https://github.com/test") == "https://github.com/test"


# --- CSP middleware tests ---


class TestCSPMiddleware:
    """Test Content-Security-Policy header middleware."""

    @pytest.mark.asyncio
    async def test_csp_header_present(self):
        """CSP middleware should add Content-Security-Policy header."""
        from app import CSPMiddleware
        assert hasattr(CSPMiddleware, 'CSP_POLICY')
        assert "default-src 'self'" in CSPMiddleware.CSP_POLICY

    def test_csp_blocks_external_scripts(self):
        """CSP policy should restrict script sources."""
        from app import CSPMiddleware
        assert "script-src" in CSPMiddleware.CSP_POLICY

    def test_csp_denies_framing(self):
        """CSP policy should prevent framing."""
        from app import CSPMiddleware
        assert "frame-ancestors 'none'" in CSPMiddleware.CSP_POLICY

    def test_csp_restricts_form_action(self):
        """CSP should restrict form action to self and Google OAuth."""
        from app import CSPMiddleware
        assert "form-action" in CSPMiddleware.CSP_POLICY
        assert "accounts.google.com" in CSPMiddleware.CSP_POLICY

    @pytest.mark.asyncio
    async def test_health_endpoint_has_csp_header(self):
        """Health endpoint response should include CSP header."""
        from httpx import AsyncClient, ASGITransport
        import app
        old_path = app.DB_PATH
        app.DB_PATH = ":memory:"
        try:
            # Initialize the database first
            async with db.managed_connection(":memory:") as conn:
                await db.init_db(conn)
            transport = ASGITransport(app=app.app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get("/health")
                assert "Content-Security-Policy" in resp.headers
                assert "X-Content-Type-Options" in resp.headers
                assert resp.headers["X-Content-Type-Options"] == "nosniff"
                assert "X-Frame-Options" in resp.headers
                assert resp.headers["X-Frame-Options"] == "DENY"
        finally:
            app.DB_PATH = old_path


# --- Template ARIA tests ---


class TestTemplateARIA:
    """Test accessibility attributes in templates."""

    def test_base_template_has_skip_link(self):
        """base.html should have a skip-to-content link."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")) as f:
            content = f.read()
        assert 'class="skip-link"' in content
        assert 'href="#main-content"' in content

    def test_base_template_has_nav_role(self):
        """base.html nav should have role=navigation."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")) as f:
            content = f.read()
        assert 'role="navigation"' in content

    def test_base_template_has_main_landmark(self):
        """base.html should wrap content in <main> landmark."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")) as f:
            content = f.read()
        assert '<main id="main-content">' in content

    def test_base_template_toast_has_aria_live(self):
        """Toast notification should have aria-live for screen readers."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")) as f:
            content = f.read()
        assert 'aria-live="polite"' in content
        assert 'role="status"' in content

    def test_dashboard_template_has_aria_labels_on_buttons(self):
        """Dashboard buttons should have aria-label attributes."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")) as f:
            content = f.read()
        assert 'aria-label="Approve reply' in content
        assert 'aria-label="Skip tweet' in content
        assert 'aria-label="Edit reply' in content

    def test_dashboard_kbd_overlay_has_dialog_role(self):
        """Keyboard overlay should have dialog role."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")) as f:
            content = f.read()
        assert 'role="dialog"' in content
        assert 'aria-modal="true"' in content

    def test_login_template_has_aria_label(self):
        """Login button should have aria-label."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "login.html")) as f:
            content = f.read()
        assert 'aria-label="Sign in with Google"' in content

    def test_base_template_has_toast_progress(self):
        """Toast should have a progress indicator div."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")) as f:
            content = f.read()
        assert 'toast-progress' in content

    def test_base_template_nav_has_aria_current(self):
        """Nav links should use aria-current for active page."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")) as f:
            content = f.read()
        assert 'aria-current=' in content

    def test_settings_template_has_save_flash(self):
        """Settings should have inline save flash feedback."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "settings.html")) as f:
            content = f.read()
        assert 'save-flash' in content

    def test_settings_signout_has_aria_label(self):
        """Settings sign-out button should have aria-label."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "settings.html")) as f:
            content = f.read()
        assert 'aria-label="Sign out of your account"' in content

    def test_base_template_stat_card_hover_glow(self):
        """Stat cards should have hover glow effect."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "base.html")) as f:
            content = f.read()
        assert 'box-shadow' in content
        assert 'rgba(88,166,255' in content


# --- Integration: routes use managed_connection ---


class TestManagedConnectionIntegration:
    """Verify routes that were refactored to use managed_connection."""

    def test_health_route_uses_managed_connection(self):
        """Health route source should use managed_connection."""
        import inspect
        from routes.health import health
        source = inspect.getsource(health)
        assert "managed_connection" in source

    def test_stats_route_uses_managed_connection(self):
        """Stats route source should use managed_connection."""
        import inspect
        from routes.stats import stats_page
        source = inspect.getsource(stats_page)
        assert "managed_connection" in source


# --- Existing feature regression ---


class TestRound2Regression:
    """Ensure Round 2 features still work after Round 3 changes."""

    @pytest.mark.asyncio
    async def test_db_init_still_works(self, tmp_path):
        """Database initialization should still create all tables."""
        db_path = str(tmp_path / "test.db")
        async with db.managed_connection(db_path) as conn:
            await db.init_db(conn)
            # Check key tables exist
            for table in ["users", "tweets", "variants", "replies", "queries", "cooldowns"]:
                cursor = await conn.execute(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                )
                row = await cursor.fetchone()
                assert row is not None, f"Table {table} should exist"

    @pytest.mark.asyncio
    async def test_user_crud_through_managed_connection(self, tmp_path):
        """CRUD operations should work through managed_connection."""
        db_path = str(tmp_path / "test.db")
        async with db.managed_connection(db_path) as conn:
            await db.init_db(conn)
            user = await db.get_or_create_user(conn, "test@example.com", "Test")
            assert user["email"] == "test@example.com"
            assert user["id"] > 0

    @pytest.mark.asyncio
    async def test_tweet_operations_through_managed_connection(self, tmp_path):
        """Tweet operations should work through managed_connection."""
        db_path = str(tmp_path / "test.db")
        async with db.managed_connection(db_path) as conn:
            await db.init_db(conn)
            user = await db.get_or_create_user(conn, "test@example.com")
            result = await db.upsert_tweet(
                conn, "t1", "a1", "Author", 1000, "test tweet", user_id=user["id"]
            )
            assert result is True
            pending = await db.get_pending_tweets(conn, user_id=user["id"])
            assert len(pending) == 1

    def test_dashboard_template_retains_swipe_support(self):
        """Dashboard should still have mobile swipe support."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")) as f:
            content = f.read()
        assert "touchstart" in content
        assert "SWIPE_THRESHOLD" in content

    def test_dashboard_template_retains_keyboard_shortcuts(self):
        """Dashboard should still have keyboard shortcuts."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")) as f:
            content = f.read()
        assert "case 'j'" in content
        assert "case 'a'" in content
        assert "kbd-overlay" in content

    def test_dashboard_template_retains_animations(self):
        """Dashboard should still have card animations."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "dashboard.html")) as f:
            content = f.read()
        assert "exiting-approve" in content
        assert "exiting-skip" in content
        assert "animateCardOut" in content

    def test_settings_retains_tone_grid(self):
        """Settings should still have tone selection grid."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "settings.html")) as f:
            content = f.read()
        assert "tone-grid" in content
        assert "tone" in content.lower()

    def test_login_retains_animations(self):
        """Login should still have fade-in animations."""
        with open(os.path.join(os.path.dirname(__file__), "..", "templates", "login.html")) as f:
            content = f.read()
        assert "login-fade-in" in content
        assert "login-glow" in content
