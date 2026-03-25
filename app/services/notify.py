"""Email notifications for build completion."""

import smtplib
import ssl
from flask import current_app


def send_build_notification(user_email, build, session_title):
    """Send email notification when a build completes."""
    host = current_app.config['SMTP_HOST']
    port = current_app.config['SMTP_PORT']
    username = current_app.config['SMTP_USER']
    password = current_app.config['SMTP_PASS']
    from_addr = current_app.config['NOTIFY_FROM'] or username

    if not all([host, username, password, user_email]):
        return False

    status = build['status']
    subject = f"gstack-auto Build {'Complete' if status == 'completed' else 'Failed'}: {session_title or 'Untitled'}"

    body = f"Your gstack-auto build has {status}.\n\n"
    if status == 'completed' and build['scores_json']:
        body += f"View your results in Mission Control.\n"
    body += f"\nBuild ID: {build['id']}\n"

    msg = f"From: {from_addr}\r\n"
    msg += f"To: {user_email}\r\n"
    msg += f"Subject: {subject}\r\n"
    msg += "Content-Type: text/plain; charset=utf-8\r\n"
    msg += "\r\n"
    msg += body

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=10) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(username, password)
            server.sendmail(from_addr, [user_email], msg.encode('utf-8'))
        return True
    except Exception:
        return False
