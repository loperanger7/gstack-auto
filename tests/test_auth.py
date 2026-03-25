"""Tests for authentication routes."""


def test_login_page(client):
    """GET /login renders the login page."""
    resp = client.get('/login')
    assert resp.status_code == 200
    assert b'gstack-auto' in resp.data


def test_login_page_shows_error(client):
    """GET /login?error=oauth_failed shows error message."""
    resp = client.get('/login?error=oauth_failed')
    assert resp.status_code == 200
    assert b'failed' in resp.data.lower()


def test_unauthenticated_redirect(client):
    """Unauthenticated users redirect to login."""
    resp = client.get('/office-hours')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_waitlist_unapproved_user(client, unapproved_user):
    """Unapproved users see the waitlist page."""
    unapproved_user['login'](client)
    resp = client.get('/waitlist')
    assert resp.status_code == 200
    assert b'on the list' in resp.data


def test_waitlist_approved_user_redirects(client, approved_user):
    """Approved users on /waitlist redirect to office hours."""
    approved_user['login'](client)
    resp = client.get('/waitlist')
    assert resp.status_code == 302
    assert '/office-hours' in resp.headers['Location']


def test_logout(client, approved_user):
    """Logout clears session and redirects to login."""
    approved_user['login'](client)
    resp = client.get('/logout')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']

    # Verify session cleared
    resp = client.get('/office-hours')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_root_redirects_to_login(client):
    """Root URL redirects to login when not authenticated."""
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/login' in resp.headers['Location']


def test_root_redirects_to_office_hours(client, approved_user):
    """Root URL redirects to office hours when authenticated."""
    approved_user['login'](client)
    resp = client.get('/')
    assert resp.status_code == 302
    assert '/office-hours' in resp.headers['Location']
