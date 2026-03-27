"""Build results dashboard, handoff ceremony, iterate, quick fix, deploy."""

import json
import secrets
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for, session,
    current_app, request, flash, jsonify,
)

from app.auth_helpers import require_approved_user
from app.models import (
    get_session, get_user_builds, get_build, get_messages,
    create_build, create_session, count_active_builds,
    add_message, complete_session, get_build_lineage,
    get_db, update_build_deploy_status,
)
from app.services.tokens import generate_build_token

builds_bp = Blueprint('builds', __name__)


# ── Atomic build creation ─────────────────────────────────

def create_build_atomic(user_id, session_id, parent_build_id=None,
                        root_session_id=None, iteration_summary=None):
    """Atomically check concurrent limit and create build in one transaction.

    Returns (build_id, build_token, error_msg). On error, build_id is None.
    """
    db = get_db()
    db.execute('BEGIN IMMEDIATE')
    try:
        if count_active_builds(user_id) >= 1:
            db.execute('ROLLBACK')
            return None, None, 'You already have an active build. Wait for it to complete.'

        placeholder_token = f'pending-{uuid.uuid4().hex[:12]}'
        build_id = create_build(
            user_id, session_id, placeholder_token,
            parent_build_id=parent_build_id,
            root_session_id=root_session_id,
            iteration_summary=iteration_summary,
            conn=db,
        )
        db.commit()
    except Exception:
        db.execute('ROLLBACK')
        raise

    # Generate real token (needs committed build_id)
    build_token = generate_build_token(user_id, build_id)
    db.execute('UPDATE builds SET build_token = ? WHERE id = ?', (build_token, build_id))
    db.commit()

    return build_id, build_token, None


# ── Handoff prompt builder ────────────────────────────────

def build_handoff_prompt(chat_session, build_token, base_url, build_id,
                         parent_build=None):
    """Build the prompt block that gets copied into Conductor.

    Uses a randomized heredoc delimiter to prevent shell injection.
    """
    spec = chat_session['spec_markdown'] or ''
    delimiter = f'SPEC_{secrets.token_hex(8)}'

    iteration_context = ''
    if parent_build:
        iteration_context = f"""
### Iteration Context

This is an iteration on build #{parent_build['id']}.
The pipeline should detect existing `output/` and run in iteration mode.
Focus on improving the existing code, not rewriting from scratch.
"""
        if parent_build.get('scores_json'):
            try:
                scores = json.loads(parent_build['scores_json'])
                iteration_context += f"\nPrior build scored {scores.get('average', '?')}/10.\n"
            except json.JSONDecodeError:
                pass

    return f"""## Build Instructions

This build was configured via gstack-auto office hours.

**IMPORTANT — First Step:** Write the Product Specification below to `product-spec.md`
before running the pipeline. The pipeline reads its spec from that file.

```bash
cat > product-spec.md << '{delimiter}'
{spec}
{delimiter}
```

### Product Specification

{spec}
{iteration_context}
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


# ── Routes ────────────────────────────────────────────────

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

    # Check for parent build (iteration flow)
    parent_build = None
    if chat_session['parent_build_id']:
        parent_build = get_build(chat_session['parent_build_id'], user['id'])

    build_id, build_token, error = create_build_atomic(
        user['id'], session_id,
        parent_build_id=chat_session['parent_build_id'] if parent_build else None,
        root_session_id=parent_build['root_session_id'] if parent_build else None,
    )

    if error:
        return render_template('handoff.html',
                               user=user,
                               chat_session=chat_session,
                               error=error)

    base_url = current_app.config['BASE_URL']
    prompt_block = build_handoff_prompt(
        chat_session, build_token, base_url, build_id,
        parent_build=parent_build,
    )

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

    lineage = get_build_lineage(build_id) if build['parent_build_id'] else []

    return render_template('build_detail.html',
                           user=user,
                           build=build,
                           scores=scores,
                           phases=phases,
                           lineage=lineage)


@builds_bp.route('/builds/<int:build_id>/iterate', methods=['POST'])
def iterate(build_id):
    """Start a full iterate flow — creates office hours session pre-seeded with parent context."""
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    build = get_build(build_id, user['id'])
    if not build or build['status'] != 'completed':
        flash('Can only iterate on completed builds.')
        return redirect(url_for('builds.index'))

    # Create session linked to parent build
    session_id = create_session(
        user['id'],
        title=f'Iterate on Build #{build_id}',
        parent_build_id=build_id,
    )

    # Pre-seed with context from parent build
    parent_session = get_session(build['session_id'])
    if parent_session and parent_session['spec_markdown']:
        preseed_content = f"This is an iteration session. The previous build (#{build_id}) produced this spec:\n\n{parent_session['spec_markdown'][:2000]}"
        if build['scores_json']:
            try:
                scores = json.loads(build['scores_json'])
                preseed_content += f"\n\nPrevious scores: {scores.get('average', '?')}/10"
            except json.JSONDecodeError:
                pass
        add_message(session_id, 'preseed', preseed_content)

    return redirect(url_for('office_hours.chat', session_id=session_id))


@builds_bp.route('/builds/<int:build_id>/quick-fix', methods=['POST'])
def quick_fix(build_id):
    """Quick fix — one-liner description, creates minimal session and goes straight to handoff."""
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    build = get_build(build_id, user['id'])
    if not build or build['status'] != 'completed':
        flash('Can only iterate on completed builds.')
        return redirect(url_for('builds.index'))

    fix_description = request.form.get('fix_description', '').strip()
    if not fix_description:
        flash('Please describe what to fix.')
        return redirect(url_for('builds.detail', build_id=build_id))

    # Create minimal session — completed immediately
    session_id = create_session(
        user['id'],
        title=f'Quick Fix: {fix_description[:50]}',
        parent_build_id=build_id,
    )

    # Build spec from parent + fix description
    parent_session = get_session(build['session_id'])
    parent_spec = parent_session['spec_markdown'] if parent_session else ''

    quick_spec = f"""# Product Specification (Quick Fix Iteration)

## Original Spec
{parent_spec[:3000]}

## Quick Fix Request
{fix_description}

## Instructions
Apply the quick fix described above to the existing codebase. This is an iteration —
improve the existing code, do not rewrite from scratch.
"""
    add_message(session_id, 'user', fix_description)
    add_message(session_id, 'assistant', 'Quick fix noted. Proceeding to build.')
    complete_session(session_id, quick_spec)

    # Go straight to handoff
    return redirect(url_for('builds.new_build', session_id=session_id))


@builds_bp.route('/builds/<int:build_id>/deploy', methods=['POST'])
def deploy(build_id):
    """Trigger async Fly.io re-deploy for a completed build."""
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    build = get_build(build_id, user['id'])
    if not build or build['status'] != 'completed':
        flash('Can only deploy completed builds.')
        return redirect(url_for('builds.index'))

    if not build['fly_app_name']:
        flash('No Fly app associated with this build.')
        return redirect(url_for('builds.detail', build_id=build_id))

    if not user['deploy_config']:
        flash('Configure your Fly API token in Settings first.')
        return redirect(url_for('settings.index'))

    from app.services.deploy import trigger_deploy
    trigger_deploy(build, user, current_app._get_current_object())

    flash('Deploy started.')
    return redirect(url_for('builds.detail', build_id=build_id))


@builds_bp.route('/builds/<int:build_id>/deploy-status')
def deploy_status(build_id):
    """Poll endpoint for deploy status (JSON)."""
    user = require_approved_user()
    if not user:
        return jsonify({'error': 'unauthorized'}), 401

    build = get_build(build_id, user['id'])
    if not build:
        return jsonify({'error': 'not found'}), 404

    return jsonify({'deploy_status': build['deploy_status'] or 'none'})
