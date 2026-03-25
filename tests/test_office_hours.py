"""Tests for office hours routes."""

import json


def test_office_hours_requires_approval(client, unapproved_user):
    """Unapproved users can't access office hours."""
    unapproved_user['login'](client)
    resp = client.get('/office-hours')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_office_hours_page(client, approved_user):
    """Approved users see the office hours page."""
    approved_user['login'](client)
    resp = client.get('/office-hours')
    assert resp.status_code == 200
    assert b'Office Hours' in resp.data


def test_new_session(client, approved_user, db):
    """Create a new chat session."""
    approved_user['login'](client)
    resp = client.post('/office-hours/new', data={'template_id': '1'})
    assert resp.status_code == 302
    assert '/office-hours/' in resp.headers['Location']

    # Verify session created in DB
    sessions = db.execute('SELECT * FROM sessions').fetchall()
    assert len(sessions) == 1
    assert sessions[0]['template_id'] == 1


def test_session_rate_limit(client, approved_user, app, db):
    """Enforce max sessions per day."""
    approved_user['login'](client)
    user_id = approved_user['user']['id']

    # Create MAX sessions
    max_sessions = app.config['MAX_SESSIONS_PER_DAY']
    for i in range(max_sessions):
        db.execute(
            'INSERT INTO sessions (user_id, title) VALUES (?, ?)',
            (user_id, f'Session {i}')
        )
    db.commit()

    # Next one should fail
    resp = client.post('/office-hours/new', data={})
    assert resp.status_code == 200
    assert b'Daily limit' in resp.data


def test_chat_page(client, approved_user, db):
    """View a chat session."""
    approved_user['login'](client)
    user_id = approved_user['user']['id']

    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) VALUES (1, ?, 'Test', 'active')",
        (user_id,)
    )
    db.commit()

    resp = client.get('/office-hours/1')
    assert resp.status_code == 200
    assert b'Test' in resp.data


def test_chat_wrong_user(client, approved_user, db):
    """Can't view another user's session."""
    approved_user['login'](client)

    db.execute(
        "INSERT INTO users (id, google_id, email, name, is_approved) VALUES (9999, 'g9999', 'other@test.com', 'Other', 1)"
    )
    db.execute(
        "INSERT INTO sessions (id, user_id, title) VALUES (1, 9999, 'Other')"
    )
    db.commit()

    resp = client.get('/office-hours/1')
    assert resp.status_code == 302  # Redirects away


def test_complete_session(client, approved_user, db):
    """Complete a session generates spec markdown."""
    approved_user['login'](client)
    user_id = approved_user['user']['id']

    db.execute(
        "INSERT INTO sessions (id, user_id, title, status) VALUES (1, ?, 'Test', 'active')",
        (user_id,)
    )
    db.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (1, 'user', 'Build me a todo app')"
    )
    db.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (1, 'assistant', 'Great idea!')"
    )
    db.commit()

    resp = client.post('/office-hours/1/complete')
    assert resp.status_code == 302
    assert '/builds/new/1' in resp.headers['Location']

    session = db.execute('SELECT * FROM sessions WHERE id = 1').fetchone()
    assert session['status'] == 'completed'
    assert session['spec_markdown'] is not None
    assert 'todo app' in session['spec_markdown']


def test_history_page(client, approved_user):
    """History page renders."""
    approved_user['login'](client)
    resp = client.get('/history')
    assert resp.status_code == 200
    assert b'Session History' in resp.data
