#!/usr/bin/env python3
"""gstack-auto server.

Serves the setup page, results dashboard, and pipeline output.
Binds to 127.0.0.1 only. No dependencies beyond Python stdlib.

Usage:
  python3 scripts/setup-server.py
"""

import difflib
import http.server
import json
import os
import re
import subprocess
import sys
from urllib.parse import parse_qs, urlparse

PORT_RANGE = (8080, 8081, 8082)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# File paths — all relative to project root
ENV_PATH = os.path.join(ROOT, '.env')
CONFIG_PATH = os.path.join(ROOT, 'pipeline', 'config.yml')
SPEC_PATH = os.path.join(ROOT, 'product-spec.md')
SETUP_PATH = os.path.join(ROOT, 'setup.html')
DASHBOARD_PATH = os.path.join(ROOT, 'dashboard.html')
STYLE_PATH = os.path.join(ROOT, 'style.css')
SEND_SCRIPT = os.path.join(ROOT, 'scripts', 'send-email.py')
OUTPUT_ROOT = os.path.join(ROOT, 'output')
RUNS_DIR = os.path.join(ROOT, '.context', 'runs')
RESULTS_HISTORY = os.path.join(ROOT, 'results-history.json')

CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.gif': 'image/gif',
    '.woff2': 'font/woff2',
}


def read_file(path):
    """Read a file or return None if it doesn't exist."""
    try:
        with open(path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None


def write_file(path, content):
    """Write content to a file. Raises on permission errors."""
    with open(path, 'w') as f:
        f.write(content)


def parse_env():
    """Read .env and return dict of key=value pairs."""
    result = {}
    text = read_file(ENV_PATH)
    if text is None:
        return result
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, v = line.split('=', 1)
            result[k.strip()] = v.strip()
    return result


def get_email_to():
    """Read email.to from config.yml."""
    text = read_file(CONFIG_PATH)
    if text is None:
        return ''
    m = re.search(r'^\s+to:\s*"?([^"\n]+)"?', text, re.MULTILINE)
    return m.group(1).strip() if m else ''


def update_config_email_to(email):
    """Update the email.to field in config.yml in place."""
    text = read_file(CONFIG_PATH)
    if text is None:
        return
    updated = re.sub(
        r'^(\s+to:\s*)"?[^"\n]*"?',
        f'\\1"{email}"',
        text,
        count=1,
        flags=re.MULTILINE,
    )
    write_file(CONFIG_PATH, updated)


def guess_content_type(path):
    ext = os.path.splitext(path)[1].lower()
    return CONTENT_TYPES.get(ext, 'application/octet-stream')


def has_scored_runs():
    """Check if any run has a score.json file."""
    if not os.path.isdir(RUNS_DIR):
        return False
    for name in os.listdir(RUNS_DIR):
        if os.path.isfile(os.path.join(RUNS_DIR, name, 'score.json')):
            return True
    return False


def collect_run_sources(run_dir):
    """Read source files from a run's output directory (skip tests/, README)."""
    files = {}
    if not os.path.isdir(run_dir):
        return files
    for name in sorted(os.listdir(run_dir)):
        fpath = os.path.join(run_dir, name)
        if not os.path.isfile(fpath) or name == 'README.md':
            continue
        try:
            with open(fpath, 'r') as f:
                files[name] = f.read().splitlines()
        except (IOError, UnicodeDecodeError):
            pass
    return files


class Handler(http.server.BaseHTTPRequestHandler):
    """
    ── Routes ────────────────────────────────────────────
    GET  /              → smart route: dashboard (if results) or setup
    GET  /setup         → setup.html
    GET  /dashboard     → dashboard.html
    GET  /style.css     → style.css
    GET  /results       → JSON: run scores + progress
    GET  /output/*      → static files from output/ (path-traversal safe)
    GET  /diff          → unified diff between two runs
    GET  /current-config→ { email, spec }
    POST /save-config   → write .env, config.yml, product-spec.md
    POST /test-email    → run send-email.py --probe
    """

    def log_message(self, fmt, *args):
        pass

    def respond(self, code, body):
        payload = json.dumps(body).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(payload))
        self.end_headers()
        self.wfile.write(payload)

    def read_body(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length)
        return json.loads(raw) if raw else {}

    def serve_file(self, path, content_type):
        content = read_file(path)
        if content is None:
            self.send_error(500, f'{os.path.basename(path)} not found')
            return
        payload = content.encode()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(payload))
        self.end_headers()
        self.wfile.write(payload)

    # ── GET ───────────────────────────────────────────────

    def do_GET(self):
        path = self.path.split('?')[0]

        if path == '/':
            self.smart_route()
        elif path == '/setup':
            self.serve_file(SETUP_PATH, 'text/html; charset=utf-8')
        elif path == '/dashboard':
            self.serve_file(DASHBOARD_PATH, 'text/html; charset=utf-8')
        elif path == '/style.css':
            self.serve_file(STYLE_PATH, 'text/css; charset=utf-8')
        elif path == '/results':
            self.get_results()
        elif path.startswith('/output/'):
            self.serve_output(path[8:])
        elif path == '/diff':
            self.get_diff()
        elif path == '/current-config':
            self.get_current_config()
        else:
            self.send_error(404)

    def smart_route(self):
        if has_scored_runs():
            self.serve_file(DASHBOARD_PATH, 'text/html; charset=utf-8')
        else:
            self.serve_file(SETUP_PATH, 'text/html; charset=utf-8')

    def get_current_config(self):
        env = parse_env()
        email = env.get('PATTAYA_SMTP_USER', '') or get_email_to()
        spec = read_file(SPEC_PATH) or ''
        self.respond(200, {'email': email, 'spec': spec})

    def get_results(self):
        if not os.path.isdir(RUNS_DIR):
            self.respond(200, {'runs': [], 'status': 'no_runs'})
            return

        runs = []
        for name in sorted(os.listdir(RUNS_DIR)):
            run_dir = os.path.join(RUNS_DIR, name)
            if not os.path.isdir(run_dir) or not name.startswith('run-'):
                continue

            score_path = os.path.join(run_dir, 'score.json')
            has_output = os.path.isdir(os.path.join(OUTPUT_ROOT, name))

            if os.path.isfile(score_path):
                try:
                    with open(score_path, 'r') as f:
                        scores = json.load(f)
                    runs.append({
                        'id': name,
                        'status': 'scored',
                        'scores': scores,
                        'has_output': has_output,
                    })
                except (json.JSONDecodeError, IOError) as e:
                    sys.stderr.write(f'Warning: bad {score_path}: {e}\n')
            else:
                phases = sorted([
                    f.replace('.md', '')
                    for f in os.listdir(run_dir)
                    if f.startswith('phase-') and f.endswith('.md')
                ])
                runs.append({
                    'id': name,
                    'status': 'in_progress',
                    'phases_completed': phases,
                    'has_output': has_output,
                })

        scored = sorted(
            [r for r in runs if r['status'] == 'scored'],
            key=lambda r: r['scores'].get('average', 0),
            reverse=True,
        )
        in_progress = [r for r in runs if r['status'] == 'in_progress']
        all_runs = scored + in_progress

        if not all_runs:
            status = 'no_runs'
        elif in_progress:
            status = 'in_progress'
        else:
            status = 'ready'

        spec = read_file(SPEC_PATH) or ''
        first_line = spec.strip().split('\n', 1)[0].lstrip('# ').strip() if spec.strip() else ''
        spec_title = first_line if first_line and first_line != 'Product Spec' else ''

        # Style name from config
        style_name = ''
        config = read_file(CONFIG_PATH) or ''
        for line in config.split('\n'):
            stripped = line.strip()
            if stripped.startswith('style:') and not stripped.startswith('#'):
                val = stripped.split(':', 1)[1].strip().strip('"').strip("'")
                if val:
                    style_path = os.path.join(ROOT, 'pipeline', 'styles', val + '.md')
                    if os.path.isfile(style_path):
                        style_content = read_file(style_path) or ''
                        heading = style_content.strip().split('\n', 1)[0].lstrip('# ').strip()
                        style_name = heading if heading else val
                    else:
                        style_name = val
                break

        # Round history from results-history.json (most recent pipeline run)
        round_history = []
        if os.path.isfile(RESULTS_HISTORY):
            try:
                with open(RESULTS_HISTORY, 'r') as f:
                    history = json.load(f)
                if isinstance(history, list):
                    for entry in reversed(history):
                        if 'round_results' in entry:
                            round_history = entry['round_results']
                            break
                elif isinstance(history, dict) and 'round_results' in history:
                    round_history = history['round_results']
            except (json.JSONDecodeError, IOError):
                pass

        self.respond(200, {
            'runs': all_runs,
            'status': status,
            'spec_title': spec_title,
            'style_name': style_name,
            'round_history': round_history,
        })

    def serve_output(self, rel_path):
        """Serve static files from output/ with path traversal protection."""
        safe_root = os.path.realpath(OUTPUT_ROOT)
        requested = os.path.realpath(os.path.join(OUTPUT_ROOT, rel_path))

        if not requested.startswith(safe_root + os.sep) and requested != safe_root:
            self.send_error(403, 'Forbidden')
            return

        if not os.path.isfile(requested):
            self.send_error(404)
            return

        content_type = guess_content_type(requested)
        try:
            with open(requested, 'rb') as f:
                content = f.read()
        except IOError:
            self.send_error(500)
            return

        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(content))
        self.end_headers()
        self.wfile.write(content)

    def get_diff(self):
        """Return unified diff between two runs' output files."""
        params = parse_qs(urlparse(self.path).query)
        run_a = (params.get('a') or [''])[0]
        run_b = (params.get('b') or [''])[0]

        if not run_a or not run_b:
            self.respond(400, {'error': 'Provide ?a=run-a&b=run-b'})
            return

        if not re.match(r'^run-[a-z]$', run_a) or not re.match(r'^run-[a-z]$', run_b):
            self.respond(400, {'error': 'Invalid run ID.'})
            return

        dir_a = os.path.join(OUTPUT_ROOT, run_a)
        dir_b = os.path.join(OUTPUT_ROOT, run_b)

        if not os.path.isdir(dir_a) or not os.path.isdir(dir_b):
            self.respond(404, {'error': 'Run output not found.'})
            return

        files_a = collect_run_sources(dir_a)
        files_b = collect_run_sources(dir_b)
        all_files = sorted(set(files_a) | set(files_b))

        diffs = []
        for name in all_files:
            a_lines = files_a.get(name, [])
            b_lines = files_b.get(name, [])
            diff = list(difflib.unified_diff(
                a_lines, b_lines,
                fromfile=f'{run_a}/{name}',
                tofile=f'{run_b}/{name}',
            ))
            if diff:
                diffs.append({'file': name, 'diff': '\n'.join(diff)})

        self.respond(200, {'diffs': diffs})

    # ── POST ──────────────────────────────────────────────

    def do_POST(self):
        if self.path == '/save-config':
            self.save_config()
        elif self.path == '/test-email':
            self.test_email()
        else:
            self.send_error(404)

    def save_config(self):
        try:
            data = self.read_body()
        except (json.JSONDecodeError, ValueError):
            self.respond(400, {'error': 'Invalid request body.'})
            return

        email = (data.get('email') or '').strip()
        password = (data.get('password') or '').replace(' ', '')
        spec = data.get('spec') or ''

        has_creds = bool(email and password)

        if not has_creds and not spec.strip():
            self.respond(400, {'error': 'Nothing to save.'})
            return

        try:
            if has_creds:
                write_file(ENV_PATH, f'PATTAYA_SMTP_USER={email}\nPATTAYA_SMTP_PASS={password}\n')
                update_config_email_to(email)

            if spec.strip():
                write_file(SPEC_PATH, spec)

            self.respond(200, {'message': 'Saved.'})

        except PermissionError as e:
            self.respond(500, {'error': f'Permission denied: {e.filename}'})

    def test_email(self):
        if not os.path.exists(ENV_PATH):
            self.respond(400, {'error': 'No .env file. Save your credentials first.'})
            return

        try:
            result = subprocess.run(
                [sys.executable, SEND_SCRIPT, '--probe'],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=ROOT,
            )
            output = (result.stdout + result.stderr).strip()

            if result.returncode == 0:
                self.respond(200, {'message': output or 'Connection OK.'})
            else:
                self.respond(400, {'error': output or 'Probe failed.'})

        except subprocess.TimeoutExpired:
            self.respond(400, {'error': 'SMTP connection timed out after 10s.'})
        except FileNotFoundError:
            self.respond(500, {'error': 'send-email.py not found.'})


def main():
    for port in PORT_RANGE:
        try:
            server = http.server.HTTPServer(('127.0.0.1', port), Handler)
            print(f'gstack-auto → http://127.0.0.1:{port}')
            server.serve_forever()
        except OSError:
            continue
    print('All ports 8080-8082 in use. Free a port and try again.')
    sys.exit(1)


if __name__ == '__main__':
    main()
