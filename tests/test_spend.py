"""Tests for daily spend ceiling."""


def test_spend_under_ceiling(app, db):
    """Check passes when under the ceiling."""
    with app.app_context():
        from app.services.spend import check_spend_allowed
        allowed, remaining = check_spend_allowed()
        assert allowed is True
        assert remaining == app.config['DAILY_TOKEN_CEILING']


def test_spend_over_ceiling(app, db):
    """Check fails when over the ceiling."""
    with app.app_context():
        from app.services.spend import check_spend_allowed, record_spend

        # Create a user first
        db.execute(
            "INSERT INTO users (id, google_id, email, is_approved) VALUES (1, 'g1', 'u@t.com', 1)"
        )
        db.commit()

        # Record spend exceeding ceiling
        ceiling = app.config['DAILY_TOKEN_CEILING']
        record_spend(user_id=1, input_tokens=ceiling + 1, output_tokens=0)

        allowed, remaining = check_spend_allowed()
        assert allowed is False
        assert remaining == 0


def test_record_spend(app, db):
    """Spend is recorded in the log."""
    with app.app_context():
        from app.services.spend import record_spend
        from app.models import get_daily_spend

        db.execute(
            "INSERT INTO users (id, google_id, email, is_approved) VALUES (1, 'g1', 'u@t.com', 1)"
        )
        db.commit()

        record_spend(user_id=1, input_tokens=1000, output_tokens=500)
        assert get_daily_spend() == 1500

        record_spend(user_id=1, input_tokens=200, output_tokens=100)
        assert get_daily_spend() == 1800
