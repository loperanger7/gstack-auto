"""Admin panel — user approval, stats, session management."""

from flask import Blueprint, render_template, redirect, url_for, session, request

from app.models import (
    get_user_by_id, get_all_users, approve_user, revoke_user, get_stats,
)

admin_bp = Blueprint('admin', __name__)


def require_admin():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = get_user_by_id(user_id)
    if not user or not user['is_admin']:
        return None
    return user


@admin_bp.route('/admin')
def index():
    user = require_admin()
    if not user:
        return redirect(url_for('auth.login'))

    users = get_all_users()
    stats = get_stats()
    return render_template('admin.html', user=user, users=users, stats=stats)


@admin_bp.route('/admin/approve/<int:user_id>', methods=['POST'])
def approve(user_id):
    admin = require_admin()
    if not admin:
        return redirect(url_for('auth.login'))

    approve_user(user_id)
    return redirect(url_for('admin.index'))


@admin_bp.route('/admin/revoke/<int:user_id>', methods=['POST'])
def revoke(user_id):
    admin = require_admin()
    if not admin:
        return redirect(url_for('auth.login'))

    # Don't let admin revoke themselves
    if user_id == admin['id']:
        return redirect(url_for('admin.index'))

    revoke_user(user_id)
    return redirect(url_for('admin.index'))
