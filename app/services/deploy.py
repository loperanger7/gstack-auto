"""Async Fly.io re-deploy via threading."""

import json
import threading
import logging
import requests

from app.models import update_build_deploy_status
from app.services.crypto import decrypt_deploy_config

logger = logging.getLogger(__name__)


def trigger_deploy(build, user, app_context):
    """Launch async deploy in a background thread.

    Args:
        build: build row (must have fly_app_name, id)
        user: user row (must have id, deploy_config)
        app_context: Flask app for pushing context in thread
    """
    fly_app_name = build['fly_app_name']
    if not fly_app_name:
        update_build_deploy_status(build['id'], 'failed:no_app_name')
        return

    deploy_config = user['deploy_config']
    if not deploy_config:
        update_build_deploy_status(build['id'], 'failed:no_deploy_config')
        return

    try:
        fly_token = decrypt_deploy_config(deploy_config)
    except Exception:
        update_build_deploy_status(build['id'], 'failed:decrypt_error')
        return

    update_build_deploy_status(build['id'], 'deploying')

    thread = threading.Thread(
        target=_deploy_worker,
        args=(build['id'], fly_app_name, fly_token, app_context),
        daemon=True,
    )
    thread.start()


def _deploy_worker(build_id, fly_app_name, fly_token, app):
    """Background worker that calls Fly Machines API to redeploy."""
    with app.app_context():
        try:
            # List machines for this app
            headers = {'Authorization': f'Bearer {fly_token}'}
            resp = requests.get(
                f'https://api.machines.dev/v1/apps/{fly_app_name}/machines',
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            machines = resp.json()

            if not machines:
                update_build_deploy_status(build_id, 'failed:no_machines')
                return

            # Restart each machine (simplest redeploy)
            for machine in machines:
                machine_id = machine.get('id')
                if not machine_id:
                    continue
                restart_resp = requests.post(
                    f'https://api.machines.dev/v1/apps/{fly_app_name}/machines/{machine_id}/restart',
                    headers=headers,
                    timeout=30,
                )
                if restart_resp.status_code not in (200, 202):
                    logger.warning('Machine %s restart failed: %s', machine_id, restart_resp.text)

            update_build_deploy_status(build_id, 'deployed')

        except requests.Timeout:
            update_build_deploy_status(build_id, 'failed:timeout')
        except requests.RequestException as e:
            logger.error('Deploy failed for build %s: %s', build_id, e)
            update_build_deploy_status(build_id, f'failed:{type(e).__name__}')
        except Exception as e:
            logger.error('Deploy unexpected error for build %s: %s', build_id, e)
            update_build_deploy_status(build_id, 'failed:unknown')
