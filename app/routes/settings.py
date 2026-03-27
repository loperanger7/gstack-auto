"""User settings — deploy config (Fly API token)."""

from flask import Blueprint, render_template, redirect, url_for, request, flash

from app.auth_helpers import require_approved_user
from app.models import get_user_deploy_config, set_user_deploy_config

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/settings')
def index():
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    has_deploy_config = bool(user['deploy_config'])
    return render_template('settings.html', user=user, has_deploy_config=has_deploy_config)


@settings_bp.route('/settings/deploy', methods=['POST'])
def save_deploy_config():
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    fly_token = request.form.get('fly_token', '').strip()

    if not fly_token:
        # Clear config
        set_user_deploy_config(user['id'], None)
        flash('Deploy config cleared.')
        return redirect(url_for('settings.index'))

    # Validate token format (Fly tokens start with specific prefixes)
    if len(fly_token) < 20:
        flash('Invalid Fly API token — too short.')
        return redirect(url_for('settings.index'))

    # Validate by making a test API call
    import requests as http_requests
    try:
        resp = http_requests.get(
            'https://api.machines.dev/v1/apps',
            headers={'Authorization': f'Bearer {fly_token}'},
            timeout=10,
        )
        if resp.status_code == 401:
            flash('Invalid Fly API token — authentication failed.')
            return redirect(url_for('settings.index'))
    except http_requests.RequestException:
        flash('Could not verify token — Fly API unreachable. Token saved anyway.')

    # Encrypt and store
    try:
        from app.services.crypto import encrypt_deploy_config
        encrypted = encrypt_deploy_config(fly_token)
        set_user_deploy_config(user['id'], encrypted)
        flash('Fly API token saved.')
    except ValueError as e:
        flash(f'Encryption error: {e}. Ask admin to set DEPLOY_ENCRYPTION_KEY.')

    return redirect(url_for('settings.index'))
