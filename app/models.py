"""SQLite database access layer."""

import sqlite3
import os
from flask import g, current_app


def get_db():
    """Get a database connection for the current request."""
    if 'db' not in g:
        db_path = current_app.config['DATABASE']
        if db_path != ':memory:':
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
        g.db.execute('PRAGMA foreign_keys=ON')
    return g.db


def close_db(e=None):
    """Close database connection at end of request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(app):
    """Run migrations on startup."""
    db_path = app.config['DATABASE']
    if db_path == ':memory:':
        return  # Tests handle their own init
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute('PRAGMA journal_mode=WAL')
    migration_dir = os.path.join(os.path.dirname(__file__), '..', 'migrations')
    if os.path.isdir(migration_dir):
        for f in sorted(os.listdir(migration_dir)):
            if f.endswith('.sql'):
                with open(os.path.join(migration_dir, f)) as mf:
                    conn.executescript(mf.read())
    conn.close()


def cleanup_expired_nonces():
    """Delete nonces older than 2 days. Called on app startup."""
    try:
        db_path = current_app.config['DATABASE']
        if db_path == ':memory:':
            return
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM nonces WHERE created_at < datetime('now', '-2 days')")
        conn.commit()
        conn.close()
    except Exception:
        pass


# ── Query helpers ──────────────────────────────────────

def get_user_by_google_id(google_id):
    db = get_db()
    return db.execute('SELECT * FROM users WHERE google_id = ?', (google_id,)).fetchone()


def get_user_by_id(user_id):
    db = get_db()
    return db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()


def create_user(google_id, email, name, avatar_url, is_admin=False, is_approved=False):
    db = get_db()
    db.execute(
        '''INSERT INTO users (google_id, email, name, avatar_url, is_admin, is_approved, last_login)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''',
        (google_id, email, name, avatar_url, int(is_admin), int(is_approved))
    )
    db.commit()
    return get_user_by_google_id(google_id)


def update_user_login(user_id):
    db = get_db()
    db.execute("UPDATE users SET last_login = datetime('now') WHERE id = ?", (user_id,))
    db.commit()


def count_sessions_today(user_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) as c FROM sessions WHERE user_id = ? AND created_at > date('now')",
        (user_id,)
    ).fetchone()
    return row['c']


def count_messages_in_session(session_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) as c FROM messages WHERE session_id = ? AND role = 'user'",
        (session_id,)
    ).fetchone()
    return row['c']


def create_session(user_id, title=None, template_id=None):
    db = get_db()
    cur = db.execute(
        'INSERT INTO sessions (user_id, title, template_id) VALUES (?, ?, ?)',
        (user_id, title, template_id)
    )
    db.commit()
    return cur.lastrowid


def get_session(session_id, user_id=None):
    db = get_db()
    if user_id:
        return db.execute(
            'SELECT * FROM sessions WHERE id = ? AND user_id = ?',
            (session_id, user_id)
        ).fetchone()
    return db.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()


def get_user_sessions(user_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC',
        (user_id,)
    ).fetchall()


def add_message(session_id, role, content):
    db = get_db()
    db.execute(
        'INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)',
        (session_id, role, content)
    )
    db.commit()


def get_messages(session_id):
    db = get_db()
    return db.execute(
        'SELECT * FROM messages WHERE session_id = ? ORDER BY created_at ASC',
        (session_id,)
    ).fetchall()


def complete_session(session_id, spec_markdown):
    db = get_db()
    db.execute(
        "UPDATE sessions SET status = 'completed', spec_markdown = ?, completed_at = datetime('now') WHERE id = ?",
        (spec_markdown, session_id)
    )
    db.commit()


def create_build(user_id, session_id, build_token):
    db = get_db()
    cur = db.execute(
        'INSERT INTO builds (user_id, session_id, build_token) VALUES (?, ?, ?)',
        (user_id, session_id, build_token)
    )
    db.commit()
    return cur.lastrowid


def get_build(build_id, user_id=None):
    db = get_db()
    if user_id:
        return db.execute(
            'SELECT * FROM builds WHERE id = ? AND user_id = ?',
            (build_id, user_id)
        ).fetchone()
    return db.execute('SELECT * FROM builds WHERE id = ?', (build_id,)).fetchone()


def get_build_by_token(token):
    db = get_db()
    return db.execute('SELECT * FROM builds WHERE build_token = ?', (token,)).fetchone()


def get_user_builds(user_id):
    db = get_db()
    return db.execute(
        'SELECT b.*, s.title as session_title FROM builds b LEFT JOIN sessions s ON b.session_id = s.id WHERE b.user_id = ? ORDER BY b.created_at DESC',
        (user_id,)
    ).fetchall()


def count_active_builds(user_id):
    db = get_db()
    row = db.execute(
        "SELECT COUNT(*) as c FROM builds WHERE user_id = ? AND status IN ('pending', 'running')",
        (user_id,)
    ).fetchone()
    return row['c']


def update_build_progress(build_id, phases_json):
    db = get_db()
    db.execute(
        "UPDATE builds SET status = 'running', phases_json = ? WHERE id = ?",
        (phases_json, build_id)
    )
    db.commit()


def complete_build(build_id, scores_json, round_results_json, conductor_url=None):
    db = get_db()
    db.execute(
        "UPDATE builds SET status = 'completed', scores_json = ?, round_results_json = ?, conductor_url = ?, completed_at = datetime('now') WHERE id = ?",
        (scores_json, round_results_json, conductor_url, build_id)
    )
    db.commit()


def fail_build(build_id):
    db = get_db()
    db.execute(
        "UPDATE builds SET status = 'failed', completed_at = datetime('now') WHERE id = ?",
        (build_id,)
    )
    db.commit()


def get_all_users():
    db = get_db()
    return db.execute('SELECT * FROM users ORDER BY created_at DESC').fetchall()


def approve_user(user_id):
    db = get_db()
    db.execute('UPDATE users SET is_approved = 1 WHERE id = ?', (user_id,))
    db.commit()


def revoke_user(user_id):
    db = get_db()
    db.execute('UPDATE users SET is_approved = 0 WHERE id = ?', (user_id,))
    db.commit()


def get_templates():
    db = get_db()
    return db.execute('SELECT * FROM templates ORDER BY sort_order ASC').fetchall()


def get_template(template_id):
    db = get_db()
    return db.execute('SELECT * FROM templates WHERE id = ?', (template_id,)).fetchone()


def store_nonce(nonce, build_id):
    db = get_db()
    db.execute('INSERT INTO nonces (nonce, build_id) VALUES (?, ?)', (nonce, build_id))
    db.commit()


def check_and_use_nonce(nonce):
    """Atomically mark nonce as used. Returns True if it was valid and unused."""
    db = get_db()
    cursor = db.execute('UPDATE nonces SET used = 1 WHERE nonce = ? AND used = 0', (nonce,))
    db.commit()
    return cursor.rowcount > 0


def record_token_spend(user_id, tokens_used):
    db = get_db()
    db.execute(
        'INSERT INTO spend_log (user_id, tokens_used) VALUES (?, ?)',
        (user_id, tokens_used)
    )
    db.commit()


def get_daily_spend():
    db = get_db()
    row = db.execute(
        "SELECT COALESCE(SUM(tokens_used), 0) as total FROM spend_log WHERE created_at > date('now')"
    ).fetchone()
    return row['total']


def get_stats():
    """Admin dashboard stats."""
    db = get_db()
    users = db.execute('SELECT COUNT(*) as c FROM users').fetchone()['c']
    approved = db.execute('SELECT COUNT(*) as c FROM users WHERE is_approved = 1').fetchone()['c']
    sessions = db.execute('SELECT COUNT(*) as c FROM sessions').fetchone()['c']
    builds = db.execute('SELECT COUNT(*) as c FROM builds').fetchone()['c']
    completed = db.execute("SELECT COUNT(*) as c FROM builds WHERE status = 'completed'").fetchone()['c']
    return {
        'total_users': users,
        'approved_users': approved,
        'total_sessions': sessions,
        'total_builds': builds,
        'completed_builds': completed,
    }
