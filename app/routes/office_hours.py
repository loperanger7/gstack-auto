"""Office hours chat UI + Claude API streaming."""

import json
from flask import (
    Blueprint, render_template, redirect, url_for, session,
    request, Response, stream_with_context, current_app
)

from app.models import (
    get_user_by_id, count_sessions_today, count_messages_in_session,
    create_session, get_session, get_user_sessions, get_messages,
    add_message, complete_session, get_templates, get_template,
)
from app.services.chat import stream_chat_response, sse_error
from app.services.spend import check_spend_allowed, record_spend

office_hours_bp = Blueprint('office_hours', __name__)


def require_approved_user():
    """Check session and return user, or None if not authorized."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    user = get_user_by_id(user_id)
    if not user or not user['is_approved']:
        return None
    return user


@office_hours_bp.route('/office-hours')
def index():
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    sessions = get_user_sessions(user['id'])
    templates = get_templates()
    return render_template('office_hours.html', user=user, sessions=sessions, templates=templates)


@office_hours_bp.route('/office-hours/new', methods=['POST'])
def new_session():
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    # Rate limit: sessions per day
    max_sessions = current_app.config['MAX_SESSIONS_PER_DAY']
    if count_sessions_today(user['id']) >= max_sessions:
        return render_template('office_hours.html',
                               user=user,
                               sessions=get_user_sessions(user['id']),
                               templates=get_templates(),
                               error=f'Daily limit reached ({max_sessions} sessions/day). Try again tomorrow.')

    template_id = request.form.get('template_id')
    template = get_template(template_id) if template_id else None
    title = template['name'] if template else 'New Session'

    session_id = create_session(user['id'], title=title, template_id=template_id)
    return redirect(url_for('office_hours.chat', session_id=session_id))


@office_hours_bp.route('/office-hours/<int:session_id>')
def chat(session_id):
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    chat_session = get_session(session_id, user['id'])
    if not chat_session:
        return redirect(url_for('office_hours.index'))

    messages = get_messages(session_id)
    template = get_template(chat_session['template_id']) if chat_session['template_id'] else None

    return render_template('chat.html',
                           user=user,
                           chat_session=chat_session,
                           messages=messages,
                           template=template)


@office_hours_bp.route('/office-hours/<int:session_id>/message', methods=['POST'])
def send_message(session_id):
    """Stream a Claude response via SSE."""
    user = require_approved_user()
    if not user:
        return Response(sse_error('api_error', 'Not authenticated'), mimetype='text/event-stream')

    chat_session = get_session(session_id, user['id'])
    if not chat_session:
        return Response(sse_error('api_error', 'Session not found'), mimetype='text/event-stream')

    if chat_session['status'] != 'active':
        return Response(sse_error('api_error', 'Session is already completed'), mimetype='text/event-stream')

    # Get message from request
    data = request.get_json(silent=True)
    if not data or not data.get('message', '').strip():
        return Response(sse_error('api_error', 'Empty message'), mimetype='text/event-stream')

    message_text = data['message'].strip()

    # Rate limit: messages per session
    max_messages = current_app.config['MAX_MESSAGES_PER_SESSION']
    if count_messages_in_session(session_id) >= max_messages:
        return Response(
            sse_error('rate_limited', f'Message limit reached ({max_messages}/session).'),
            mimetype='text/event-stream'
        )

    # Spend ceiling check
    allowed, remaining = check_spend_allowed()
    if not allowed:
        return Response(
            sse_error('rate_limited', 'Daily API usage limit reached. Try again tomorrow.'),
            mimetype='text/event-stream'
        )

    # Store user message
    add_message(session_id, 'user', message_text)

    # Get conversation history
    messages = get_messages(session_id)
    template = get_template(chat_session['template_id']) if chat_session['template_id'] else None

    def generate():
        full_response = ''
        input_tokens = 0
        output_tokens = 0

        for chunk in stream_chat_response(messages, template):
            yield chunk

            # Parse done event to get full response + tokens
            if chunk.startswith('event: done'):
                try:
                    data_line = chunk.split('\n')[1]
                    if data_line.startswith('data: '):
                        done_data = json.loads(data_line[6:])
                        full_response = done_data.get('full_text', '')
                        input_tokens = done_data.get('input_tokens', 0)
                        output_tokens = done_data.get('output_tokens', 0)
                except (json.JSONDecodeError, IndexError):
                    pass

        # Store assistant response
        if full_response:
            add_message(session_id, 'assistant', full_response)

        # Record spend
        if input_tokens or output_tokens:
            record_spend(user['id'], input_tokens, output_tokens)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        }
    )


@office_hours_bp.route('/office-hours/<int:session_id>/complete', methods=['POST'])
def complete(session_id):
    """Complete the session and generate spec markdown."""
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    chat_session = get_session(session_id, user['id'])
    if not chat_session:
        return redirect(url_for('office_hours.index'))

    messages = get_messages(session_id)

    # Build spec from conversation
    spec_parts = [f"# Product Specification\n\nGenerated from office hours session: {chat_session['title']}\n"]
    for msg in messages:
        prefix = '**User:**' if msg['role'] == 'user' else '**Consultant:**'
        spec_parts.append(f"{prefix} {msg['content']}")

    spec_markdown = '\n\n'.join(spec_parts)
    complete_session(session_id, spec_markdown)

    return redirect(url_for('builds.new_build', session_id=session_id))


@office_hours_bp.route('/history')
def history():
    user = require_approved_user()
    if not user:
        return redirect(url_for('auth.login'))

    sessions = get_user_sessions(user['id'])
    return render_template('history.html', user=user, sessions=sessions)
