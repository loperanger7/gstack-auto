#!/usr/bin/env python3
"""Smoke test: environment variables round-trip through the server."""

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, 'scripts', 'setup-server.py')
ENV_PATH = os.path.join(ROOT, '.env')
SPEC_PATH = os.path.join(ROOT, 'product-spec.md')
CONFIG_PATH = os.path.join(ROOT, 'pipeline', 'config.yml')
PORT = 8089  # Use a high port to avoid conflicts

def post(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f'http://127.0.0.1:{PORT}{path}',
        data=data,
        headers={'Content-Type': 'application/json'},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())

def get(path):
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}{path}') as resp:
        return json.loads(resp.read())

def main():
    # Backup files that save_config() modifies
    backups = {}
    for path in (ENV_PATH, SPEC_PATH, CONFIG_PATH):
        if os.path.exists(path):
            with open(path) as f:
                backups[path] = f.read()

    proc = None
    try:
        # Start server on test port
        proc = subprocess.Popen(
            [sys.executable, SERVER, '--port', str(PORT)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=ROOT,
        )
        # Wait for server to be ready
        for _ in range(20):
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{PORT}/')
                break
            except Exception:
                time.sleep(0.25)
        else:
            print('FAIL: server did not start')
            sys.exit(1)

        passed = 0
        failed = 0

        # Test 1: Save env vars
        res = post('/save-config', {
            'spec': 'test spec',
            'env_vars': {'ODDS_API_KEY': 'test-key-123', 'WEATHER_KEY': 'wx-456'},
        })
        assert res.get('message') == 'Saved.', f'Test 1 failed: {res}'
        passed += 1
        print('PASS: save env vars')

        # Test 2: Verify .env file contents
        with open(ENV_PATH) as f:
            env_text = f.read()
        assert 'ODDS_API_KEY=test-key-123' in env_text, f'Test 2a failed: ODDS_API_KEY not in .env'
        assert 'WEATHER_KEY=wx-456' in env_text, f'Test 2b failed: WEATHER_KEY not in .env'
        passed += 1
        print('PASS: .env contains user env vars')

        # Test 3: GET /current-config returns has-value flags (not actual values)
        config = get('/current-config')
        env_vars = config.get('env_vars', {})
        assert env_vars.get('ODDS_API_KEY') is True, f'Test 3a failed: {env_vars}'
        assert env_vars.get('WEATHER_KEY') is True, f'Test 3b failed: {env_vars}'
        # Must NOT contain PATTAYA_ keys
        for k in env_vars:
            assert not k.startswith('PATTAYA_'), f'Test 3c failed: PATTAYA_ key leaked: {k}'
        passed += 1
        print('PASS: current-config returns env var flags')

        # Test 4: Save SMTP creds — env vars survive
        res = post('/save-config', {
            'email': 'test@example.com',
            'password': 'testpass1234567x',
            'spec': 'test spec',
        })
        assert res.get('message') == 'Saved.', f'Test 4 failed: {res}'
        with open(ENV_PATH) as f:
            env_text = f.read()
        assert 'ODDS_API_KEY=test-key-123' in env_text, f'Test 4a failed: env var lost after SMTP save'
        assert 'PATTAYA_SMTP_USER=test@example.com' in env_text, f'Test 4b failed: SMTP not saved'
        passed += 1
        print('PASS: SMTP save preserves env vars')

        # Test 5: Delete an env var (empty string)
        res = post('/save-config', {
            'spec': 'test spec',
            'env_vars': {'WEATHER_KEY': ''},
        })
        assert res.get('message') == 'Saved.', f'Test 5 failed: {res}'
        with open(ENV_PATH) as f:
            env_text = f.read()
        assert 'WEATHER_KEY' not in env_text, f'Test 5a failed: WEATHER_KEY not deleted'
        assert 'ODDS_API_KEY=test-key-123' in env_text, f'Test 5b failed: other key lost'
        passed += 1
        print('PASS: delete env var via empty string')

        # Test 6: PATTAYA_ prefix rejected
        res = post('/save-config', {
            'spec': 'test spec',
            'env_vars': {'PATTAYA_HACK': 'bad'},
        })
        # Should save but PATTAYA_HACK should be silently dropped
        with open(ENV_PATH) as f:
            env_text = f.read()
        assert 'PATTAYA_HACK' not in env_text, f'Test 6 failed: PATTAYA_ prefix not blocked'
        passed += 1
        print('PASS: PATTAYA_ prefix blocked')

        print(f'\n{passed}/{passed + failed} tests passed')
        sys.exit(0 if failed == 0 else 1)

    except AssertionError as e:
        print(f'FAIL: {e}')
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: {e}')
        sys.exit(1)
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
        # Restore all backed-up files
        for path, content in backups.items():
            with open(path, 'w') as f:
                f.write(content)
        # Remove .env if it didn't exist before the test
        if ENV_PATH not in backups and os.path.exists(ENV_PATH):
            os.remove(ENV_PATH)

if __name__ == '__main__':
    main()
