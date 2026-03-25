"""Daily token spend ceiling enforcement."""

from flask import current_app
from app.models import get_daily_spend, record_token_spend


def check_spend_allowed():
    """Check if we're under the daily token ceiling.

    Returns (allowed: bool, remaining: int).
    """
    ceiling = current_app.config['DAILY_TOKEN_CEILING']
    if ceiling <= 0:
        return True, 0  # No ceiling configured

    spent = get_daily_spend()
    remaining = ceiling - spent
    return remaining > 0, max(0, remaining)


def record_spend(user_id, input_tokens, output_tokens):
    """Record token usage for a chat interaction."""
    total = input_tokens + output_tokens
    if total > 0:
        record_token_spend(user_id, total)
