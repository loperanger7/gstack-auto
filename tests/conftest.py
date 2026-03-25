"""Test fixtures for gstack-auto-as-a-service."""

import os
import sqlite3
import pytest
from app import create_app
from app.config import TestConfig


@pytest.fixture
def app(tmp_path):
    """Create a test app with a temp database."""
    db_path = str(tmp_path / 'test.db')

    class TmpConfig(TestConfig):
        DATABASE = db_path

    test_app = create_app(TmpConfig)
    yield test_app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Database connection for test assertions."""
    with app.app_context():
        from app.models import get_db
        yield get_db()


@pytest.fixture
def approved_user(app, db):
    """Create an approved user and return user dict + session setup."""
    db.execute(
        '''INSERT INTO users (google_id, email, name, is_approved, is_admin)
           VALUES ('google-123', 'user@test.com', 'Test User', 1, 0)'''
    )
    db.commit()
    user = db.execute('SELECT * FROM users WHERE google_id = ?', ('google-123',)).fetchone()

    def login(client):
        with client.session_transaction() as sess:
            sess['user_id'] = user['id']
            sess.permanent = True
        return user

    return {'user': user, 'login': login}


@pytest.fixture
def admin_user(app, db):
    """Create an admin user."""
    db.execute(
        '''INSERT INTO users (google_id, email, name, is_approved, is_admin)
           VALUES ('google-admin', 'admin@test.com', 'Admin', 1, 1)'''
    )
    db.commit()
    user = db.execute('SELECT * FROM users WHERE google_id = ?', ('google-admin',)).fetchone()

    def login(client):
        with client.session_transaction() as sess:
            sess['user_id'] = user['id']
            sess.permanent = True
        return user

    return {'user': user, 'login': login}


@pytest.fixture
def unapproved_user(app, db):
    """Create an unapproved user."""
    db.execute(
        '''INSERT INTO users (google_id, email, name, is_approved, is_admin)
           VALUES ('google-pending', 'pending@test.com', 'Pending User', 0, 0)'''
    )
    db.commit()
    user = db.execute('SELECT * FROM users WHERE google_id = ?', ('google-pending',)).fetchone()

    def login(client):
        with client.session_transaction() as sess:
            sess['user_id'] = user['id']
            sess.permanent = True
        return user

    return {'user': user, 'login': login}
