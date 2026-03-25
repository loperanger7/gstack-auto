"""Tests for build routes."""


def test_builds_page_empty(client, approved_user):
    """Builds page shows empty state."""
    approved_user['login'](client)
    resp = client.get('/builds')
    assert resp.status_code == 200
    assert b'No builds yet' in resp.data


def test_handoff_requires_completed_session(client, approved_user, db):
    """Handoff page requires a completed session."""
    approved_user['login'](client)
    user_id = approved_user['user']['id']

    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) VALUES (1, ?, 'Test', 'active')",
        (user_id,)
    )
    db.commit()

    resp = client.get('/builds/new/1')
    assert resp.status_code == 302  # Redirects to chat


def test_handoff_creates_build(client, approved_user, db):
    """Handoff ceremony creates a build with token."""
    approved_user['login'](client)
    user_id = approved_user['user']['id']

    db.execute(
        "INSERT INTO sessions (id, user_id, title, status, spec_markdown) VALUES (1, ?, 'Test', 'completed', '# Spec')",
        (user_id,)
    )
    db.commit()

    resp = client.get('/builds/new/1')
    assert resp.status_code == 200
    assert b'Build Handoff' in resp.data
    assert b'Copy' in resp.data

    # Verify build created
    builds = db.execute('SELECT * FROM builds WHERE user_id = ?', (user_id,)).fetchall()
    assert len(builds) == 1
    assert builds[0]['build_token'] is not None


def test_concurrent_build_limit(client, approved_user, db):
    """Only 1 active build per user."""
    approved_user['login'](client)
    user_id = approved_user['user']['id']

    db.execute(
        "INSERT INTO sessions (id, user_id, title, status, spec_markdown) VALUES (1, ?, 'Test', 'completed', '# Spec')",
        (user_id,)
    )
    db.execute(
        "INSERT INTO builds (user_id, session_id, build_token, status) VALUES (?, 1, 'tok1', 'running')",
        (user_id,)
    )
    db.commit()

    resp = client.get('/builds/new/1')
    assert resp.status_code == 200
    assert b'already have an active build' in resp.data


def test_build_detail(client, approved_user, db):
    """View a build's detail page."""
    approved_user['login'](client)
    user_id = approved_user['user']['id']

    db.execute(
        "INSERT INTO builds (id, user_id, build_token, status, scores_json) VALUES (1, ?, 'tok', 'completed', '{\"average\": 7.5, \"functionality\": 8}')",
        (user_id,)
    )
    db.commit()

    resp = client.get('/builds/1')
    assert resp.status_code == 200
    assert b'7.5' in resp.data


def test_build_detail_wrong_user(client, approved_user, db):
    """Can't view another user's build."""
    approved_user['login'](client)

    db.execute(
        "INSERT INTO users (id, google_id, email, name, is_approved) VALUES (9999, 'g9999', 'other@test.com', 'Other', 1)"
    )
    db.execute(
        "INSERT INTO builds (id, user_id, build_token, status) VALUES (1, 9999, 'tok', 'pending')"
    )
    db.commit()

    resp = client.get('/builds/1')
    assert resp.status_code == 302  # Redirects
