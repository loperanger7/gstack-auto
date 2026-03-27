"""Machine API endpoints — results POST, progress POST."""

import json
import re
from flask import Blueprint, request, jsonify

from app.models import (
    get_build_by_token, get_build, update_build_progress, complete_build,
    fail_build, get_user_by_id, update_build_deploy_status,
)
from app.services.tokens import validate_build_token, verify_payload_integrity
from app.services.notify import send_build_notification

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


def extract_token():
    """Extract and validate bearer token from Authorization header."""
    auth = request.headers.get('Authorization', '')
    if not auth.startswith('Bearer '):
        return None, jsonify({'error': 'Missing or invalid Authorization header'}), 401

    token = auth[7:]
    payload = validate_build_token(token)
    if not payload:
        return None, jsonify({'error': 'Invalid or expired token'}), 401

    return payload, None, None


@api_bp.route('/results', methods=['POST'])
def receive_results():
    """Receive final build results from the pipeline.

    Validates: JWT → nonce one-time-use → store results.
    """
    payload, error_response, status = extract_token()
    if error_response:
        return error_response, status

    # Parse body BEFORE consuming nonce — failed parse shouldn't burn the token
    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON body'}), 400

    if not data:
        return jsonify({'error': 'Empty payload'}), 400

    # Verify nonce (one-time-use) — after body validation so parse failures are retryable
    valid, err = verify_payload_integrity(payload, request.get_data())
    if not valid:
        return jsonify({'error': err}), 403

    build_id = payload.get('build_id')
    user_id = payload.get('user_id')
    build = get_build(build_id, user_id)
    if not build:
        return jsonify({'error': 'Build not found'}), 404

    status_val = data.get('status', 'completed')
    scores_json = json.dumps(data.get('scores', {}))
    round_results_json = json.dumps(data.get('round_results', []))

    # Validate conductor_url — must be https or empty
    conductor_url = data.get('conductor_workspace', '')
    if conductor_url and not conductor_url.startswith('https://'):
        conductor_url = ''

    # Store fly_app_name if provided (for deploy feature) — validate format
    fly_app_name = data.get('fly_app_name', '')
    if fly_app_name and not re.match(r'^[a-z0-9][a-z0-9-]{0,62}$', fly_app_name):
        fly_app_name = ''

    if status_val == 'failed':
        fail_build(build_id)
    else:
        complete_build(build_id, scores_json, round_results_json, conductor_url)

    # Store fly_app_name on build record
    if fly_app_name:
        from app.models import get_db
        db = get_db()
        db.execute('UPDATE builds SET fly_app_name = ? WHERE id = ?', (fly_app_name, build_id))
        db.commit()

    # Send email notification (best-effort)
    user = get_user_by_id(payload.get('user_id'))
    if user:
        build = get_build(build_id)
        send_build_notification(user['email'], build, data.get('spec_title', ''))

    # Auto-deploy if user has deploy config and fly_app_name is set (best-effort)
    if fly_app_name and status_val != 'failed' and user and user['deploy_config']:
        try:
            from flask import current_app
            from app.services.deploy import trigger_deploy
            build = get_build(build_id)
            trigger_deploy(build, user, current_app._get_current_object())
        except Exception:
            pass  # Auto-deploy is best-effort

    return jsonify({'status': 'ok', 'build_id': build_id}), 200


@api_bp.route('/progress', methods=['POST'])
def receive_progress():
    """Receive per-phase progress updates from the pipeline."""
    payload, error_response, status = extract_token()
    if error_response:
        return error_response, status

    try:
        data = request.get_json(force=True)
    except Exception:
        return jsonify({'error': 'Invalid JSON body'}), 400

    if not data:
        return jsonify({'error': 'Empty payload'}), 400

    build_id = payload.get('build_id')
    user_id = payload.get('user_id')
    build = get_build(build_id, user_id)
    if not build:
        return jsonify({'error': 'Build not found'}), 404

    # Merge progress into existing phases
    existing = {}
    if build['phases_json']:
        try:
            existing = json.loads(build['phases_json'])
        except json.JSONDecodeError:
            pass

    phase = data.get('phase', '')
    phase_status = data.get('status', 'running')
    if phase:
        existing[phase] = phase_status

    update_build_progress(build_id, json.dumps(existing))

    return jsonify({'status': 'ok'}), 200
