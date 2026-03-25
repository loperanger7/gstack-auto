"""Build results dashboard and handoff ceremony."""

import json
from flask import Blueprint, render_template, redirect, url_for, session, current_app

from app.models import (
    get_user_by_id, get_session, get_user_builds, get_build,
    create_build, count_active_builds,
)
from app.services.tokens import generate_build_token

builds_bp = Blueprint('builds', __name__)


def require_approved_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = get_user_by_id(user_id)
    if not user or not user['is_approved']:
        return None
    return user


@builds_bp.route('/builds')
def index():
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    builds = get_user_builds(user['id'])
    return render_template('builds.html', user=user, builds=builds)


@builds_bp.route('/builds/new/<int:session_id>')
def new_build(session_id):
    """Handoff ceremony — generate build token and show copy-paste prompt."""
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    chat_session = get_session(session_id, user['id'])
    if not chat_session:
        return redirect(url_for('office_hours.index'))

    if chat_session['status'] != 'completed':
        return redirect(url_for('office_hours.chat', session_id=session_id))

    # Check concurrent build limit (1 active per user) — atomic check-and-create
    from app.models import get_db
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    try:
        if count_active_builds(user['id']) >= 1:
            db.execute('ROLLBACK')
            return render_template('handoff.html',
                                   user=user,
                                   chat_session=chat_session,
                                   error='You already have an active build. Wait for it to complete.')

        build_id = create_build(user['id'], session_id, 'pending')
        build_token = generate_build_token(user['id'], build_id)
        db.execute('UPDATE builds SET build_token = ? WHERE id = ?', (build_token, build_id))
        db.commit()
    except Exception:
        db.execute('ROLLBACK')
        raise

    # Build the handoff prompt
    base_url = current_app.config['BASE_URL']
    prompt_block = build_handoff_prompt(chat_session, build_token, base_url, build_id)

    return render_template('handoff.html',
                           user=user,
                           chat_session=chat_session,
                           build_id=build_id,
                           prompt_block=prompt_block,
                           build_token=build_token)


@builds_bp.route('/builds/<int:build_id>')
def detail(build_id):
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    build = get_build(build_id, user['id'])
    if not build:
        return redirect(url_for('builds.index'))

    scores = None
    if build['scores_json']:
        try:
            scores = json.loads(build['scores_json'])
        except json.JSONDecodeError:
            pass

    phases = None
    if build['phases_json']:
        try:
            phases = json.loads(build['phases_json'])
        except json.JSONDecodeError:
            pass

    return render_template('build_detail.html',
                           user=user,
                           build=build,
                           scores=scores,
                           phases=phases)


def build_handoff_prompt(chat_session, build_token, base_url, build_id):
    """Build the prompt block that gets copied into Conductor."""
    spec = chat_session['spec_markdown'] or ''

    return f"""## Build Instructions

This build was configured via gstack-auto office hours.

### Product Specification

{spec}

### Build Configuration

Set these environment variables before running the pipeline:

```
MISSION_CONTROL_URL={base_url}
BUILD_TOKEN={build_token}
BUILD_ID={build_id}
```

The pipeline will POST progress updates to {base_url}/api/v1/progress
and final results to {base_url}/api/v1/results using the BUILD_TOKEN
for authentication.
"""
