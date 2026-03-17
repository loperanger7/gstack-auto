#!/usr/bin/env python3
"""gstack-auto server.

Serves the Mission Control UI and pipeline output.
Binds to 127.0.0.1 only. No dependencies beyond Python stdlib.

Usage:
  python3 scripts/setup-server.py
"""

import difflib
import http.server
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, urlparse

PORT_RANGE = (8080, 8081, 8082)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# File paths — all relative to project root
ENV_PATH = os.path.join(ROOT, '.env')
CONFIG_PATH = os.path.join(ROOT, 'pipeline', 'config.yml')
SPEC_PATH = os.path.join(ROOT, 'product-spec.md')
INDEX_PATH = os.path.join(ROOT, 'index.html')
STYLES_DIR = os.path.join(ROOT, 'pipeline', 'styles')
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


def get_user_env_vars():
    """Return non-PATTAYA_ env vars from .env as {key: True} flags (never expose values)."""
    env = parse_env()
    return {k: True for k in env if not k.startswith('PATTAYA_')}


def save_env(updates):
    """Read-modify-write .env: merge updates into existing keys. Empty value = delete key."""
    env = parse_env()
    for k, v in updates.items():
        if v == '' or v is None:
            env.pop(k, None)
        else:
            env[k] = v
    lines = [f'{k}={v}\n' for k, v in env.items()]
    write_file(ENV_PATH, ''.join(lines))


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


def update_config_value(key, value):
    """Update a top-level key in config.yml. Uncomments if commented out.

    Skips indented keys (nested YAML). If the key doesn't exist at all,
    appends it. Uses string values for style, integers for numeric fields.
    """
    text = read_file(CONFIG_PATH)
    if text is None:
        return

    # Try to find the key — commented or uncommented, top-level only
    pattern = re.compile(
        r'^(#\s*)?' + re.escape(key) + r':\s*"?[^"\n]*"?',
        re.MULTILINE,
    )
    match = pattern.search(text)
    if match:
        # Replace the matched line with the uncommented, updated value
        if isinstance(value, int):
            replacement = f'{key}: {value}'
        else:
            replacement = f'{key}: "{value}"'
        updated = text[:match.start()] + replacement + text[match.end():]
    else:
        # Key not found — append before the email block
        if isinstance(value, int):
            line = f'{key}: {value}\n'
        else:
            line = f'{key}: "{value}"\n'
        updated = text.rstrip('\n') + '\n\n' + line

    write_file(CONFIG_PATH, updated)


def get_config_value(key, default=''):
    """Read a top-level scalar value from config.yml."""
    text = read_file(CONFIG_PATH)
    if text is None:
        return default
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.startswith(key + ':'):
            val = stripped.split(':', 1)[1].strip().strip('"').strip("'")
            return val if val else default
    return default


def get_style_profiles():
    """Scan pipeline/styles/*.md and return profile metadata.

    Each profile .md has: line 1 = # Name, first blockquote = signature quote,
    ## Principles section = coding principles, ## Review Focus = review focus.
    """
    profiles = []
    if not os.path.isdir(STYLES_DIR):
        return profiles

    for fname in sorted(os.listdir(STYLES_DIR)):
        if not fname.endswith('.md'):
            continue
        fpath = os.path.join(STYLES_DIR, fname)
        content = read_file(fpath)
        if not content:
            continue

        name = fname[:-3]  # strip .md
        lines = content.strip().split('\n')

        # Extract display name from # heading
        display = lines[0].lstrip('# ').strip() if lines and lines[0].startswith('#') else name

        # Extract quote from first blockquote line
        quote = ''
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith('>'):
                quote = stripped.lstrip('> ').strip('"').strip()
                break

        # Extract principles section
        principles = []
        in_principles = False
        for line in lines:
            if line.startswith('## Principles'):
                in_principles = True
                continue
            if in_principles and line.startswith('## '):
                break
            if in_principles and line.strip().startswith('- **'):
                # Extract the bold principle name
                m = re.match(r'- \*\*(.+?)\.\*\*', line.strip())
                if m:
                    principles.append(m.group(1))

        profiles.append({
            'name': name,
            'display': display,
            'quote': quote,
            'principles': principles,
        })

    return profiles


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
    GET  /              → index.html (Mission Control)
    GET  /setup         → redirect to /
    GET  /dashboard     → redirect to /
    GET  /style.css     → style.css
    GET  /styles        → JSON: available style profiles
    GET  /results       → JSON: run scores + progress
    GET  /output/*      → static files from output/ (path-traversal safe)
    GET  /diff          → unified diff between two runs
    GET  /current-config→ { email, spec, parallel_runs, rounds, style }
    POST /save-config   → write .env, config.yml, product-spec.md
    POST /test-email    → run send-email.py --probe
    POST /new-project   → clear runs, output, spec → return to SETUP
    POST /create-repo   → validate, create GitHub repo, push winner, enable Pages
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

        if path == '/' or path == '/setup' or path == '/dashboard':
            self.serve_file(INDEX_PATH, 'text/html; charset=utf-8')
        elif path == '/style.css':
            self.serve_file(STYLE_PATH, 'text/css; charset=utf-8')
        elif path == '/styles':
            self.get_styles()
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

    def get_current_config(self):
        env = parse_env()
        email = env.get('PATTAYA_SMTP_USER', '') or get_email_to()
        spec = read_file(SPEC_PATH) or ''
        self.respond(200, {
            'email': email,
            'spec': spec,
            'parallel_runs': int(get_config_value('parallel_runs', '3')),
            'rounds': int(get_config_value('rounds', '1')),
            'style': get_config_value('style', ''),
            'env_vars': get_user_env_vars(),
        })

    def get_styles(self):
        self.respond(200, get_style_profiles())

    def get_results(self):
        if not os.path.isdir(RUNS_DIR):
            self.respond(200, {
                'runs': [], 'status': 'no_runs',
                'spec_title': '', 'style_name': '',
                'round_history': [], 'has_winner_output': False,
            })
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

        # Check if a winner-final output exists (with an actual index.html)
        winner_final_path = os.path.join(OUTPUT_ROOT, 'winner-final', 'index.html')
        has_winner_output = os.path.isfile(winner_final_path)

        self.respond(200, {
            'runs': all_runs,
            'status': status,
            'spec_title': spec_title,
            'style_name': style_name,
            'round_history': round_history,
            'has_winner_output': has_winner_output,
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
        elif self.path == '/new-project':
            self.new_project()
        elif self.path == '/create-repo':
            self.create_repo()
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

        env_vars = data.get('env_vars') or {}

        has_creds = bool(email and password)
        has_pipeline_config = any(
            k in data for k in ('parallel_runs', 'rounds', 'style')
        )
        has_env_vars = bool(env_vars)

        if not has_creds and not spec.strip() and not has_pipeline_config and not has_env_vars:
            self.respond(400, {'error': 'Nothing to save.'})
            return

        try:
            env_updates = {}
            if has_creds:
                env_updates['PATTAYA_SMTP_USER'] = email
                env_updates['PATTAYA_SMTP_PASS'] = password
                update_config_email_to(email)
            for k, v in env_vars.items():
                key = re.sub(r'[^A-Z0-9_]', '_', k.upper())
                if key and not key.startswith('PATTAYA_'):
                    env_updates[key] = str(v)
            if env_updates:
                save_env(env_updates)

            if spec.strip():
                write_file(SPEC_PATH, spec)

            if 'parallel_runs' in data:
                val = max(1, int(data['parallel_runs']))
                update_config_value('parallel_runs', val)
            if 'rounds' in data:
                val = max(1, int(data['rounds']))
                update_config_value('rounds', val)
            if 'style' in data:
                update_config_value('style', str(data['style']))

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

    def new_project(self):
        """Clear project state and return to SETUP. Preserves config and credentials."""
        try:
            if os.path.isdir(RUNS_DIR):
                shutil.rmtree(RUNS_DIR)
                sys.stderr.write('Cleared .context/runs/\n')
            if os.path.isdir(OUTPUT_ROOT):
                shutil.rmtree(OUTPUT_ROOT)
                sys.stderr.write('Cleared output/\n')
            write_file(SPEC_PATH, '')
            self.respond(200, {'message': 'Project cleared.'})
        except PermissionError as e:
            self.respond(500, {'error': f'Permission denied: {e.filename}'})

    def create_repo(self):
        """Create a GitHub repo from winner-final output.

        Flow (local-first to avoid orphan repos):
          1. Validate inputs
          2. Copy winner-final → tmpdir, git init + commit (local only)
          3. gh repo create (creates remote)
          4. git push (fills remote)
          5. gh api to enable Pages (optional, non-fatal)
          6. Clean up tmpdir (always, via finally)
        """
        REPO_NAME_RE = re.compile(r'^[a-zA-Z0-9._-]{1,100}$')

        try:
            data = self.read_body()
        except (json.JSONDecodeError, ValueError):
            self.respond(400, {'error': 'Invalid request body.'})
            return

        repo_name = (data.get('repo_name') or '').strip()
        enable_pages = bool(data.get('enable_pages', True))

        # ── Validate at the boundary ────────────────────────
        if not repo_name or not REPO_NAME_RE.match(repo_name):
            self.respond(400, {
                'error': 'Invalid repo name. Use letters, numbers, hyphens, '
                         'underscores, dots. Max 100 characters.'
            })
            return

        winner_dir = os.path.join(OUTPUT_ROOT, 'winner-final')
        if not os.path.isdir(winner_dir) or not os.listdir(winner_dir):
            self.respond(400, {
                'error': 'No winner output to publish. Run the pipeline first.'
            })
            return

        if not shutil.which('gh'):
            self.respond(400, {
                'error': 'gh CLI not found. Install it: https://cli.github.com'
            })
            return

        visibility = '--public' if enable_pages else '--private'
        tmpdir = tempfile.mkdtemp(prefix='pattaya-repo-')

        try:
            # ── Step 1: Local prep (fail before creating anything remote) ──
            for item in os.listdir(winner_dir):
                src = os.path.join(winner_dir, item)
                dst = os.path.join(tmpdir, item)
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            def run_git(*args, timeout=30):
                return subprocess.run(
                    ['git'] + list(args),
                    cwd=tmpdir, capture_output=True, text=True, timeout=timeout,
                )

            r = run_git('init')
            if r.returncode != 0:
                self.respond(500, {'error': f'git init failed: {r.stderr.strip()}'})
                return

            run_git('config', 'user.email', 'pattaya@gstack-auto')
            run_git('config', 'user.name', 'gstack-auto')
            run_git('add', '.')
            r = run_git('commit', '-m', 'Initial commit — built by gstack-auto')
            if r.returncode != 0:
                self.respond(500, {'error': f'git commit failed: {r.stderr.strip()}'})
                return

            # ── Step 2: Create remote repo ────────────────────
            r = subprocess.run(
                ['gh', 'repo', 'create', repo_name, visibility,
                 '--description', 'Built by gstack-auto'],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode != 0:
                stderr = r.stderr.strip().lower()
                if 'already exists' in stderr or 'name already' in stderr:
                    self.respond(409, {
                        'error': f'Repository "{repo_name}" already exists.'
                    })
                elif 'auth' in stderr or 'login' in stderr:
                    self.respond(400, {
                        'error': 'GitHub not authenticated. Run: gh auth login'
                    })
                else:
                    self.respond(400, {
                        'error': f'Failed to create repo: {r.stderr.strip()}'
                    })
                return

            repo_url = r.stdout.strip()
            if not repo_url:
                repo_url = f'https://github.com/{repo_name}'
            sys.stderr.write(f'Created repo: {repo_url}\n')

            # ── Step 3: Push ──────────────────────────────────
            remote_url = repo_url
            if not remote_url.endswith('.git'):
                remote_url += '.git'
            run_git('remote', 'add', 'origin', remote_url)
            run_git('branch', '-M', 'main')
            r = run_git('push', '-u', 'origin', 'main', timeout=60)
            if r.returncode != 0:
                self.respond(500, {
                    'error': f'Push failed: {r.stderr.strip()}. '
                             f'Repo was created at {repo_url} — '
                             'you may want to delete it manually.'
                })
                return

            # ── Step 4: Enable GitHub Pages (non-fatal) ───────
            result = {'message': 'Repository created.', 'repo_url': repo_url}
            if enable_pages:
                parts = repo_url.rstrip('/').split('/')
                if len(parts) >= 2:
                    owner_repo = parts[-2] + '/' + parts[-1]
                    r = subprocess.run(
                        ['gh', 'api', f'repos/{owner_repo}/pages',
                         '--method', 'POST',
                         '-f', 'build_type=legacy',
                         '-f', 'source[branch]=main',
                         '-f', 'source[path]=/'],
                        capture_output=True, text=True, timeout=15,
                    )
                    if r.returncode == 0:
                        result['pages_url'] = (
                            f'https://{parts[-2]}.github.io/{parts[-1]}/'
                        )
                    else:
                        sys.stderr.write(
                            f'Pages API failed: {r.stderr.strip()}\n'
                        )
                        result['pages_warning'] = (
                            'GitHub Pages could not be enabled automatically. '
                            'Enable it in repo Settings > Pages.'
                        )

            self.respond(200, result)

        except subprocess.TimeoutExpired:
            self.respond(504, {
                'error': 'GitHub request timed out. Try again.'
            })
        except Exception as e:
            self.respond(500, {'error': f'Unexpected error: {e}'})
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    ports = PORT_RANGE
    if len(sys.argv) >= 3 and sys.argv[1] == '--port':
        ports = (int(sys.argv[2]),)
    for port in ports:
        try:
            server = http.server.HTTPServer(('127.0.0.1', port), Handler)
            print(f'gstack-auto → http://127.0.0.1:{port}')
            server.serve_forever()
        except OSError:
            continue
    print('All ports in use. Free a port and try again.')
    sys.exit(1)


if __name__ == '__main__':
    main()
