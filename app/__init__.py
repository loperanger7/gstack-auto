"""Flask app factory for gstack-auto-as-a-service."""

import json
import os
from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import Config
from app.models import close_db, init_db


def create_app(config=None):
    app = Flask(
        __name__,
        template_folder='templates',
        static_folder='static',
    )

    if config:
        app.config.from_object(config)
    else:
        app.config.from_object(Config)

    # Session config — Flask signed cookies
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = not app.debug
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24h
    app.config['PREFERRED_URL_SCHEME'] = 'https' if not app.debug else 'http'

    # Trust Fly.io reverse proxy headers (X-Forwarded-For, X-Forwarded-Proto, etc.)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # DB teardown
    app.teardown_appcontext(close_db)

    # Run migrations
    with app.app_context():
        init_db(app)

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.office_hours import office_hours_bp
    from app.routes.builds import builds_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp
    from app.routes.settings import settings_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(office_hours_bp)
    app.register_blueprint(builds_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(settings_bp)

    # Custom Jinja2 filters
    @app.template_filter('from_json')
    def from_json_filter(value):
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return {}

    # CSP header
    @app.after_request
    def add_security_headers(response):
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' https://lh3.googleusercontent.com data:; "
            "connect-src 'self'; "
            "frame-src 'none'; "
            "object-src 'none'"
        )
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    # Health endpoint
    @app.route('/health')
    def health():
        try:
            from app.models import get_db
            db = get_db()
            db.execute('SELECT 1')
            return {'status': 'ok'}, 200
        except Exception as e:
            return {'status': 'error', 'detail': str(e)}, 503

    # Root redirect
    @app.route('/')
    def index():
        from flask import redirect, session, url_for
        if 'user_id' in session:
            return redirect(url_for('office_hours.index'))
        return redirect(url_for('auth.login'))

    return app
