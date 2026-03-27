"""Tests for iteration features — iterate, quick fix, lineage, preseed filtering."""

import json


def setup_completed_build(db, user_id=1, build_id=1, session_id=1):
    """Create a user, session, and completed build for iteration tests."""
    db.execute(
        "INSERT OR IGNORE INTO users (id, google_id, email, name, is_approved) "
        "VALUES (?, 'g1', 'u@t.com', 'Test User', 1)",
        (user_id,)
    )
    db.execute(
        "INSERT INTO sessions (id, user_id, title, status, spec_markdown) "
        "VALUES (?, ?, 'Test App', 'completed', '# Test Spec\nBuild a test app')",
        (session_id, user_id)
    )
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, "
        "scores_json, root_session_id) VALUES (?, ?, ?, 'tok1', 'completed', "
        "'{\"average\": 7.5}', ?)",
        (build_id, user_id, session_id, session_id)
    )
    db.commit()


def login(client, db, user_id=1):
    """Log in as a test user."""
    with client.session_transaction() as sess:
        sess['user_id'] = user_id


# ── Iterate route ──────────────────────────────────────

def test_iterate_creates_session_with_parent(client, db):
    """POST /builds/<id>/iterate creates a new session linked to parent build."""
    setup_completed_build(db)
    login(client, db)

    resp = client.post('/builds/1/iterate', follow_redirects=False)
    assert resp.status_code == 302
    assert '/office-hours/' in resp.headers['Location']

    # Check session was created with parent_build_id
    session = db.execute(
        'SELECT * FROM sessions WHERE parent_build_id = 1'
    ).fetchone()
    assert session is not None
    assert 'Iterate on Build #1' in session['title']


def test_iterate_adds_preseed_message(client, db):
    """Iterate pre-seeds the session with parent context."""
    setup_completed_build(db)
    login(client, db)

    client.post('/builds/1/iterate')

    session = db.execute(
        'SELECT * FROM sessions WHERE parent_build_id = 1'
    ).fetchone()
    msg = db.execute(
        "SELECT * FROM messages WHERE session_id = ? AND role = 'preseed'",
        (session['id'],)
    ).fetchone()
    assert msg is not None
    assert 'iteration session' in msg['content'].lower()


def test_iterate_rejects_non_completed(client, db):
    """Cannot iterate on a non-completed build."""
    setup_completed_build(db)
    db.execute("UPDATE builds SET status = 'running' WHERE id = 1")
    db.commit()
    login(client, db)

    resp = client.post('/builds/1/iterate', follow_redirects=True)
    assert b'Can only iterate on completed builds' in resp.data


def test_iterate_rejects_wrong_user(client, db):
    """Cannot iterate on another user's build."""
    setup_completed_build(db)
    db.execute(
        "INSERT INTO users (id, google_id, email, name, is_approved) "
        "VALUES (2, 'g2', 'u2@t.com', 'User 2', 1)"
    )
    db.commit()
    login(client, db, user_id=2)

    resp = client.post('/builds/1/iterate', follow_redirects=True)
    assert b'Can only iterate on completed builds' in resp.data


# ── Quick Fix route ────────────────────────────────────

def test_quick_fix_creates_completed_session(client, db):
    """Quick fix creates a completed session and redirects to handoff."""
    setup_completed_build(db)
    login(client, db)

    resp = client.post('/builds/1/quick-fix',
                       data={'fix_description': 'Fix the login button color'},
                       follow_redirects=False)
    assert resp.status_code == 302
    assert '/builds/new/' in resp.headers['Location']

    session = db.execute(
        "SELECT * FROM sessions WHERE parent_build_id = 1 AND status = 'completed'"
    ).fetchone()
    assert session is not None
    assert 'Quick Fix' in session['title']
    assert 'Fix the login button color' in session['spec_markdown']


def test_quick_fix_empty_description(client, db):
    """Quick fix rejects empty description."""
    setup_completed_build(db)
    login(client, db)

    resp = client.post('/builds/1/quick-fix',
                       data={'fix_description': ''},
                       follow_redirects=True)
    assert b'describe what to fix' in resp.data


def test_quick_fix_preserves_parent_spec(client, db):
    """Quick fix spec includes the parent build's spec."""
    setup_completed_build(db)
    login(client, db)

    client.post('/builds/1/quick-fix',
                data={'fix_description': 'Add dark mode'})

    session = db.execute(
        "SELECT * FROM sessions WHERE parent_build_id = 1 AND status = 'completed'"
    ).fetchone()
    assert '# Test Spec' in session['spec_markdown']
    assert 'Add dark mode' in session['spec_markdown']


# ── Preseed filtering ─────────────────────────────────

def test_preseed_filtered_from_spec(client, db):
    """Preseed messages are excluded from the generated spec markdown."""
    setup_completed_build(db)
    login(client, db)

    # Create a session with preseed + user + assistant messages
    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) "
        "VALUES (10, 1, 'Test Session', 'active')"
    )
    db.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (10, 'preseed', 'PRESEED CONTEXT HERE')"
    )
    db.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (10, 'user', 'Build a todo app')"
    )
    db.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (10, 'assistant', 'Great idea!')"
    )
    db.commit()

    resp = client.post('/office-hours/10/complete', follow_redirects=False)
    assert resp.status_code == 302

    session = db.execute('SELECT * FROM sessions WHERE id = 10').fetchone()
    assert 'PRESEED CONTEXT HERE' not in session['spec_markdown']
    assert 'Build a todo app' in session['spec_markdown']


# ── Build lineage ─────────────────────────────────────

def test_build_lineage_query(db):
    """get_build_lineage returns ancestor chain."""
    from app.models import get_build_lineage

    setup_completed_build(db)

    # Create child build
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, "
        "parent_build_id, root_session_id) VALUES (2, 1, 1, 'tok2', 'completed', 1, 1)"
    )
    # Create grandchild build
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, "
        "parent_build_id, root_session_id) VALUES (3, 1, 1, 'tok3', 'running', 2, 1)"
    )
    db.commit()

    lineage = get_build_lineage(3)
    assert len(lineage) == 3
    assert lineage[0]['id'] == 3  # Most recent first
    assert lineage[1]['id'] == 2
    assert lineage[2]['id'] == 1


def test_build_detail_shows_lineage(client, db):
    """Build detail page shows iteration history for iterated builds."""
    setup_completed_build(db)
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, "
        "parent_build_id, root_session_id, scores_json) "
        "VALUES (2, 1, 1, 'tok2', 'completed', 1, 1, '{\"average\": 8.0}')"
    )
    db.commit()
    login(client, db)

    resp = client.get('/builds/2')
    assert resp.status_code == 200
    assert b'Iteration History' in resp.data
    assert b'Build #1' in resp.data


def test_build_detail_shows_iteration_badge(client, db):
    """Build detail shows iteration badge for child builds."""
    setup_completed_build(db)
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, "
        "parent_build_id, root_session_id) VALUES (2, 1, 1, 'tok2', 'completed', 1, 1)"
    )
    db.commit()
    login(client, db)

    resp = client.get('/builds/2')
    assert b'iteration of' in resp.data


# ── Builds list badges ────────────────────────────────

def test_builds_list_shows_iteration_badge(client, db):
    """Builds list shows iteration badge for child builds."""
    setup_completed_build(db)
    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) VALUES (2, 1, 'Iter', 'completed')"
    )
    db.execute(
        "INSERT INTO builds (id, user_id, session_id, build_token, status, "
        "parent_build_id, root_session_id) VALUES (2, 1, 2, 'tok2', 'completed', 1, 1)"
    )
    db.commit()
    login(client, db)

    resp = client.get('/builds')
    assert resp.status_code == 200
    # The iteration badge shows ↻ #parent_id
    assert '↻' in resp.data.decode()


# ── Action row on build detail ────────────────────────

def test_completed_build_shows_action_row(client, db):
    """Completed build detail shows iterate and quick fix actions."""
    setup_completed_build(db)
    login(client, db)

    resp = client.get('/builds/1')
    assert resp.status_code == 200
    assert b'Quick Fix' in resp.data
    assert b'Iterate' in resp.data


def test_pending_build_no_action_row(client, db):
    """Pending build detail does not show action row."""
    setup_completed_build(db)
    db.execute("UPDATE builds SET status = 'pending' WHERE id = 1")
    db.commit()
    login(client, db)

    resp = client.get('/builds/1')
    assert resp.status_code == 200
    assert b'Quick Fix' not in resp.data


# ── Handoff prompt ────────────────────────────────────

def test_handoff_prompt_randomized_delimiter(client, db):
    """Handoff prompt uses randomized heredoc delimiter."""
    from app.routes.builds import build_handoff_prompt
    from unittest.mock import MagicMock

    session_mock = MagicMock()
    session_mock.__getitem__ = lambda s, k: '# Test Spec' if k == 'spec_markdown' else None

    prompt = build_handoff_prompt(session_mock, 'tok', 'http://example.com', 1)
    # Should NOT contain the static 'SPEC_EOF' delimiter
    assert 'SPEC_EOF' not in prompt
    # Should contain SPEC_ prefix with random hex
    assert 'SPEC_' in prompt


def test_iteration_handoff_includes_context(client, db):
    """Iteration handoff prompt includes parent build context."""
    from app.routes.builds import build_handoff_prompt
    from unittest.mock import MagicMock

    session_mock = MagicMock()
    session_mock.__getitem__ = lambda s, k: '# Test Spec' if k == 'spec_markdown' else None

    parent = {'id': 1, 'scores_json': '{"average": 7.5}'}
    prompt = build_handoff_prompt(session_mock, 'tok', 'http://example.com', 2,
                                  parent_build=parent)
    assert 'iteration' in prompt.lower()
    assert '7.5' in prompt


# ── Conductor URL validation ──────────────────────────

def test_results_validates_conductor_url(client, app, db):
    """Results POST rejects non-https conductor URLs."""
    from tests.test_api import make_token, compute_sha, setup_build

    setup_build(db)  # Uses test_api helper which creates nonce
    token = make_token(app)
    body = json.dumps({
        'status': 'completed',
        'scores': {},
        'conductor_workspace': 'javascript:alert(1)',
    })
    sha = compute_sha('test-nonce', body.encode())

    resp = client.post('/api/v1/results',
                       data=body, content_type='application/json',
                       headers={'Authorization': f'Bearer {token}',
                                'X-Payload-SHA': sha})
    assert resp.status_code == 200

    build = db.execute('SELECT * FROM builds WHERE id = 1').fetchone()
    assert build['conductor_url'] == ''  # Rejected non-https


# ── Fly app name storage ─────────────────────────────

def test_results_stores_fly_app_name(client, app, db):
    """Results POST stores fly_app_name on build record."""
    from tests.test_api import make_token, compute_sha, setup_build

    setup_build(db)  # Uses test_api helper which creates nonce
    token = make_token(app)

    body = json.dumps({
        'status': 'completed',
        'scores': {},
        'fly_app_name': 'my-cool-app',
    })
    sha = compute_sha('test-nonce', body.encode())

    resp = client.post('/api/v1/results',
                       data=body, content_type='application/json',
                       headers={'Authorization': f'Bearer {token}',
                                'X-Payload-SHA': sha})
    assert resp.status_code == 200

    build = db.execute('SELECT * FROM builds WHERE id = 1').fetchone()
    assert build['fly_app_name'] == 'my-cool-app'
