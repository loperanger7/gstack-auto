#!/usr/bin/env python3
"""Pattaya email sender — sends pipeline results via SMTP.

Usage:
  send-email.py --probe              # Test SMTP connection (pre-flight)
  send-email.py --send BODY_FILE     # Send email with body from file

Reads config from pipeline/config.yml and credentials from .env.
Exit code 0 = success, 1 = failure with diagnostic message.
"""

import argparse
import os
import smtplib
import ssl
import sys
import re

def load_env():
    """Load .env file into environment (simple key=value parser)."""
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if not os.path.exists(env_path):
        print("FAIL: .env file not found. Copy .env.example to .env and fill in credentials.")
        print(f"  Expected at: {os.path.abspath(env_path)}")
        sys.exit(1)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

def load_config():
    """Load email config from pipeline/config.yml."""
    try:
        import yaml
    except ImportError:
        # Minimal YAML parser for our simple config
        return load_config_minimal()

    config_path = os.path.join(os.path.dirname(__file__), '..', 'pipeline', 'config.yml')
    if not os.path.exists(config_path):
        print("FAIL: pipeline/config.yml not found.")
        sys.exit(1)
    with open(config_path) as f:
        return yaml.safe_load(f)

def load_config_minimal():
    """Parse the email section from config.yml without PyYAML."""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'pipeline', 'config.yml')
    if not os.path.exists(config_path):
        print("FAIL: pipeline/config.yml not found.")
        sys.exit(1)

    config = {'email': {}}
    in_email = False
    in_smtp = False
    with open(config_path) as f:
        for line in f:
            stripped = line.rstrip()
            if stripped.startswith('email:'):
                in_email = True
                in_smtp = False
                continue
            if in_email and stripped.startswith('  smtp:'):
                in_smtp = True
                config['email']['smtp'] = {}
                continue
            if in_email and not stripped.startswith(' '):
                in_email = False
                in_smtp = False
                continue
            if in_smtp and stripped.startswith('    '):
                parts = stripped.strip().split(':', 1)
                if len(parts) == 2:
                    config['email']['smtp'][parts[0].strip()] = parts[1].strip().strip('"').strip("'")
            elif in_email and stripped.startswith('  ') and not stripped.startswith('  smtp'):
                parts = stripped.strip().split(':', 1)
                if len(parts) == 2:
                    config['email'][parts[0].strip()] = parts[1].strip().strip('"').strip("'")
    return config

def resolve_env_var(value):
    """Resolve $ENV_VAR references to actual values."""
    if value and value.startswith('$'):
        var_name = value[1:]
        resolved = os.environ.get(var_name, '')
        if not resolved:
            print(f"FAIL: Environment variable {var_name} is not set.")
            print(f"  Add it to your .env file: {var_name}=your_value")
            sys.exit(1)
        return resolved
    return value

def safe_error(msg, password):
    """Print error message with password redacted."""
    if password:
        msg = msg.replace(password, '****')
    return msg

def get_smtp_config(config):
    """Extract and validate SMTP settings."""
    email_cfg = config.get('email', {})

    to_addr = email_cfg.get('to', '')
    if not to_addr:
        print("FAIL: email.to not configured in pipeline/config.yml.")
        sys.exit(1)
    if '@' not in to_addr:
        print(f"FAIL: email.to doesn't look like an email address: {to_addr}")
        sys.exit(1)

    method = email_cfg.get('method', 'smtp')
    if method == 'file-only':
        return None  # Signal to skip email

    smtp_cfg = email_cfg.get('smtp', {})
    host = smtp_cfg.get('host', 'smtp.gmail.com')
    port = int(smtp_cfg.get('port', 587))
    username = resolve_env_var(smtp_cfg.get('username', '$PATTAYA_SMTP_USER'))
    password = resolve_env_var(smtp_cfg.get('password', '$PATTAYA_SMTP_PASS'))

    if not username:
        print("FAIL: SMTP username is empty. Check .env file.")
        sys.exit(1)
    if not password:
        print("FAIL: SMTP password is empty. Check .env file.")
        sys.exit(1)

    return {
        'to': to_addr,
        'host': host,
        'port': port,
        'username': username,
        'password': password,
    }

def probe(config):
    """Test SMTP connection and authentication without sending."""
    smtp_cfg = get_smtp_config(config)
    if smtp_cfg is None:
        print("OK: email.method is file-only — skipping probe.")
        return

    password = smtp_cfg['password']
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_cfg['host'], smtp_cfg['port'], timeout=10) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(smtp_cfg['username'], smtp_cfg['password'])
            print(f"OK: Email probe succeeded — {smtp_cfg['host']}:{smtp_cfg['port']} authenticated as {smtp_cfg['username']}")
    except smtplib.SMTPAuthenticationError as e:
        print(safe_error(f"FAIL: Authentication failed — check your App Password.\n  {e}", password))
        sys.exit(1)
    except ConnectionRefusedError:
        print(f"FAIL: Connection refused on {smtp_cfg['host']}:{smtp_cfg['port']}. Check host and port.")
        sys.exit(1)
    except TimeoutError:
        print(f"FAIL: Connection timed out to {smtp_cfg['host']}:{smtp_cfg['port']}. Check firewall/VPN.")
        sys.exit(1)
    except ssl.SSLError as e:
        print(safe_error(f"FAIL: TLS handshake failed — {e}. Try port 465 with SSL or port 587 with STARTTLS.", password))
        sys.exit(1)
    except Exception as e:
        print(safe_error(f"FAIL: {type(e).__name__}: {e}", password))
        sys.exit(1)

def send(config, body_file, subject):
    """Send email via SMTP."""
    smtp_cfg = get_smtp_config(config)
    if smtp_cfg is None:
        print("SKIP: email.method is file-only — email not sent.")
        return

    if not os.path.exists(body_file):
        print(f"FAIL: Body file not found: {body_file}")
        sys.exit(1)

    with open(body_file) as f:
        body = f.read()

    recipients = [addr.strip() for addr in smtp_cfg['to'].split(',')]
    from_addr = smtp_cfg['username']
    password = smtp_cfg['password']

    # Compose message
    msg = f"From: {from_addr}\r\n"
    msg += f"To: {smtp_cfg['to']}\r\n"
    msg += f"Subject: {subject}\r\n"
    msg += "Content-Type: text/plain; charset=utf-8\r\n"
    msg += "\r\n"
    msg += body

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP(smtp_cfg['host'], smtp_cfg['port'], timeout=30) as server:
            server.ehlo()
            server.starttls(context=ctx)
            server.ehlo()
            server.login(smtp_cfg['username'], smtp_cfg['password'])
            server.sendmail(from_addr, recipients, msg.encode('utf-8'))
            print(f"OK: Email sent to {smtp_cfg['to']}")
    except smtplib.SMTPAuthenticationError as e:
        print(safe_error(f"FAIL: Authentication failed — check your App Password.\n  {e}", password))
        sys.exit(1)
    except smtplib.SMTPRecipientsRefused as e:
        print(safe_error(f"FAIL: Recipient rejected: {e}", password))
        sys.exit(1)
    except smtplib.SMTPDataError as e:
        print(safe_error(f"FAIL: Server rejected message: {e}", password))
        sys.exit(1)
    except smtplib.SMTPServerDisconnected as e:
        print(safe_error(f"FAIL: Server disconnected: {e}. Try again.", password))
        sys.exit(1)
    except (ConnectionRefusedError, TimeoutError, ssl.SSLError) as e:
        print(safe_error(f"FAIL: {type(e).__name__}: {e}", password))
        sys.exit(1)
    except Exception as e:
        print(safe_error(f"FAIL: {type(e).__name__}: {e}", password))
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='Pattaya email sender')
    parser.add_argument('--probe', action='store_true', help='Test SMTP connection')
    parser.add_argument('--send', metavar='BODY_FILE', help='Send email with body from file')
    parser.add_argument('--subject', default='Pattaya Pipeline Results', help='Email subject line')
    args = parser.parse_args()

    if not args.probe and not args.send:
        parser.print_help()
        sys.exit(1)

    load_env()
    config = load_config()

    if args.probe:
        probe(config)
    elif args.send:
        send(config, args.send, args.subject)

if __name__ == '__main__':
    main()
