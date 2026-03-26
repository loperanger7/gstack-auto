"""Google OAuth + invite-only authentication."""

import secrets
from flask import Blueprint, redirect, url_for, session, request, render_template, current_app
from authlib.integrations.flask_client import OAuth

from app.models import get_user_by_google_id, create_user, update_user_login

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()


def init_oauth(app):
    """Initialize OAuth with app config. Called lazily on first use."""
    oauth.init_app(app)
    if 'google' not in oauth._registry:
        oauth.register(
            name='google',
            client_id=app.config['GOOGLE_CLIENT_ID'],
            client_secret=app.config['GOOGLE_CLIENT_SECRET'],
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={'scope': 'openid email profile'},
        )


@auth_bp.route('/login')
def login():
    error = request.args.get('error')
    return render_template('login.html', error=error)


@auth_bp.route('/auth/google/login')
def google_login():
    init_oauth(current_app)
    redirect_uri = url_for('auth.google_callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/google/callback')
def google_callback():
    init_oauth(current_app)
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        return redirect(url_for('auth.login', error='oauth_failed'))

    userinfo = token.get('userinfo', {})
    if not userinfo:
        return redirect(url_for('auth.login', error='oauth_failed'))

    google_id = userinfo.get('sub', '')
    email = userinfo.get('email', '')
    name = userinfo.get('name', '')
    avatar_url = userinfo.get('picture', '')

    if not google_id or not email:
        return redirect(url_for('auth.login', error='oauth_failed'))

    user = get_user_by_google_id(google_id)

    if not user:
        # New user — check if admin email
        admin_email = current_app.config.get('ADMIN_EMAIL', '')
        is_admin = bool(admin_email and email.lower() == admin_email.lower())
        is_approved = is_admin  # Admin is auto-approved

        user = create_user(
            google_id=google_id,
            email=email,
            name=name,
            avatar_url=avatar_url,
            is_admin=is_admin,
            is_approved=is_approved,
        )
    else:
        update_user_login(user['id'])

    # Session rotation on login
    session.clear()
    session['user_id'] = user['id']
    session.permanent = True
    # Regenerate session ID by setting a new random token
    session['_fresh'] = secrets.token_urlsafe(16)

    if not user['is_approved']:
        return redirect(url_for('auth.waitlist'))

    return redirect(url_for('office_hours.index'))


@auth_bp.route('/waitlist')
def waitlist():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    from app.models import get_user_by_id
    user = get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))
    if user['is_approved']:
        return redirect(url_for('office_hours.index'))
    return render_template('waitlist.html', user=user)


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
