"""Shared authentication helpers used across blueprints."""

from flask import session, redirect, url_for
from app.models import get_user_by_id


def require_approved_user():
    """Check session and return approved user, or None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = get_user_by_id(user_id)
    if not user or not user['is_approved']:
        return None
    return user
