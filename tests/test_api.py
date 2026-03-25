"""Tests for machine API endpoints."""

import json
import time
import jwt


def make_token(app, user_id=1, build_id=1, nonce='test-nonce', expired=False):
    """Helper to create a JWT build token for testing."""
    payload = {
        'user_id': user_id,
        'build_id': build_id,
        'nonce': nonce,
        'iat': int(time.time()),
        'exp': int(time.time()) + (-3600 if expired else 86400),
    }
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')


def setup_build(db, user_id=1, build_id=1, nonce='test-nonce'):
    """Create user and build in DB for API tests."""
    db.execute(
        "INSERT OR IGNORE INTO users (id, google_id, email, name, is_approved) VALUES (?, 'g1', 'u@t.com', 'U', 1)",
        (user_id,)
    )
    db.execute(
        "INSERT INTO builds (id, user_id, build_token, status) VALUES (?, ?, 'tok', 'pending')",
        (build_id, user_id)
    )
    db.execute(
        "INSERT INTO nonces (nonce, build_id) VALUES (?, ?)",
        (nonce, build_id)
    )
    db.commit()


def test_results_missing_auth(client):
    """POST /api/v1/results without auth returns 401."""
    resp = client.post('/api/v1/results', json={'status': 'completed'})
    assert resp.status_code == 401


def test_results_expired_token(client, app, db):
    """POST /api/v1/results with expired token returns 401."""
    setup_build(db)
    token = make_token(app, expired=True)
    resp = client.post('/api/v1/results',
                       json={'status': 'completed'},
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 401


def test_results_success(client, app, db):
    """POST /api/v1/results with valid token stores results."""
    setup_build(db)
    token = make_token(app)

    scores = {'average': 7.5, 'functionality': 8}
    resp = client.post('/api/v1/results',
                       json={
                           'status': 'completed',
                           'scores': scores,
                           'round_results': [],
                           'spec_title': 'Test Build',
                       },
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200

    build = db.execute('SELECT * FROM builds WHERE id = 1').fetchone()
    assert build['status'] == 'completed'
    assert '7.5' in build['scores_json']


def test_results_nonce_reuse(client, app, db):
    """Nonce can only be used once."""
    setup_build(db)
    token = make_token(app)

    # First request succeeds
    resp = client.post('/api/v1/results',
                       json={'status': 'completed', 'scores': {}},
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200

    # Second request with same nonce fails
    resp = client.post('/api/v1/results',
                       json={'status': 'completed', 'scores': {}},
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 403


def test_results_empty_body(client, app, db):
    """POST /api/v1/results with empty body returns 400."""
    setup_build(db)
    token = make_token(app)

    resp = client.post('/api/v1/results',
                       data='',
                       content_type='application/json',
                       headers={'Authorization': f'Bearer {token}'})
    # Empty body should return 400
    assert resp.status_code in (400, 403)


def test_results_failed_build(client, app, db):
    """POST with status=failed marks build as failed."""
    setup_build(db)
    token = make_token(app)

    resp = client.post('/api/v1/results',
                       json={'status': 'failed'},
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200

    build = db.execute('SELECT * FROM builds WHERE id = 1').fetchone()
    assert build['status'] == 'failed'


def test_progress_success(client, app, db):
    """POST /api/v1/progress stores phase progress."""
    setup_build(db)
    token = make_token(app)

    resp = client.post('/api/v1/progress',
                       json={'phase': '01', 'status': 'done'},
                       headers={'Authorization': f'Bearer {token}'})
    assert resp.status_code == 200

    build = db.execute('SELECT * FROM builds WHERE id = 1').fetchone()
    phases = json.loads(build['phases_json'])
    assert phases['01'] == 'done'


def test_progress_accumulates(client, app, db):
    """Multiple progress POSTs accumulate."""
    setup_build(db)
    token = make_token(app)

    client.post('/api/v1/progress',
                json={'phase': '01', 'status': 'done'},
                headers={'Authorization': f'Bearer {token}'})
    client.post('/api/v1/progress',
                json={'phase': '02', 'status': 'running'},
                headers={'Authorization': f'Bearer {token}'})

    build = db.execute('SELECT * FROM builds WHERE id = 1').fetchone()
    phases = json.loads(build['phases_json'])
    assert phases['01'] == 'done'
    assert phases['02'] == 'running'


def test_health_endpoint(client):
    """GET /health returns 200."""
    resp = client.get('/health')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['status'] == 'ok'
