"""Tests for admin routes."""


def test_admin_requires_admin(client, approved_user):
    """Non-admin users can't access admin page."""
    approved_user['login'](client)
    resp = client.get('/admin')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_admin_page(client, admin_user):
    """Admin users see the admin page."""
    admin_user['login'](client)
    resp = client.get('/admin')
    assert resp.status_code == 200
    assert b'Admin' in resp.data
    assert b'admin@test.com' in resp.data


def test_approve_user(client, admin_user, db):
    """Admin can approve a user."""
    admin_user['login'](client)

    # Create a pending user
    db.execute(
        "INSERT INTO users (id, google_id, email, name, is_approved) VALUES (99, 'g99', 'new@test.com', 'New', 0)"
    )
    db.commit()

    resp = client.post('/admin/approve/99')
    assert resp.status_code == 302

    user = db.execute('SELECT * FROM users WHERE id = 99').fetchone()
    assert user['is_approved'] == 1


def test_revoke_user(client, admin_user, db):
    """Admin can revoke a user."""
    admin_user['login'](client)

    db.execute(
        "INSERT INTO users (id, google_id, email, name, is_approved) VALUES (99, 'g99', 'rev@test.com', 'Rev', 1)"
    )
    db.commit()

    resp = client.post('/admin/revoke/99')
    assert resp.status_code == 302

    user = db.execute('SELECT * FROM users WHERE id = 99').fetchone()
    assert user['is_approved'] == 0


def test_admin_cant_revoke_self(client, admin_user, db):
    """Admin can't revoke themselves."""
    admin_user['login'](client)
    admin_id = admin_user['user']['id']

    resp = client.post(f'/admin/revoke/{admin_id}')
    assert resp.status_code == 302

    user = db.execute('SELECT * FROM users WHERE id = ?', (admin_id,)).fetchone()
    assert user['is_approved'] == 1  # Still approved


def test_admin_stats(client, admin_user, db):
    """Admin page shows stats."""
    admin_user['login'](client)

    # Create some data
    db.execute("INSERT INTO sessions (user_id, title) VALUES (1, 'Test')")
    db.commit()

    resp = client.get('/admin')
    assert resp.status_code == 200
    # Should show stats section
    assert b'Stats' in resp.data
