"""Claude API streaming wrapper for office hours chat."""

import json
from flask import current_app
import anthropic


SYSTEM_PROMPT = """You are a senior product consultant helping a customer define what they want to build. Your job is to ask smart questions, clarify requirements, identify edge cases, and produce a crystal-clear product specification.

Guidelines:
- Ask one question at a time. Don't overwhelm with multiple questions.
- Start by understanding the core problem they're solving.
- Progressively get more specific: audience → features → technical constraints → design preferences.
- When you have enough information, offer to write the spec.
- The spec should be detailed enough for an autonomous development pipeline to build it.
- Include: product description, user stories, technical requirements, UI/UX preferences, and success criteria.
- Be warm but efficient. Respect their time.
- If they're unsure, offer concrete suggestions based on what they've described."""


def get_template_system_addition(template):
    """Get additional system prompt from a template."""
    if template and template['system_prompt_addition']:
        return f"\n\nTemplate context: {template['system_prompt_addition']}"
    return ""


def stream_chat_response(messages, template=None):
    """Stream a Claude response as SSE events.

    Yields SSE-formatted strings: 'data: {...}\n\n'
    Final event: 'event: done\ndata: {}\n\n'
    Error event: 'event: error\ndata: {"type": "...", "message": "..."}\n\n'

    Returns the full response text via the generator's return value isn't
    directly accessible, so we track it via a mutable container.
    """
    api_key = current_app.config['ANTHROPIC_API_KEY']
    if not api_key:
        yield sse_error('api_error', 'Anthropic API key not configured')
        return

    system = SYSTEM_PROMPT + get_template_system_addition(template)

    # Convert our DB messages to Claude format
    claude_messages = []
    for msg in messages:
        claude_messages.append({
            'role': msg['role'],
            'content': msg['content'],
        })

    client = anthropic.Anthropic(api_key=api_key)

    full_response = ''
    input_tokens = 0
    output_tokens = 0

    try:
        with client.messages.stream(
            model='claude-sonnet-4-20250514',
            max_tokens=4096,
            system=system,
            messages=claude_messages,
        ) as stream:
            for event in stream:
                if hasattr(event, 'type'):
                    if event.type == 'content_block_delta':
                        text = event.delta.text
                        full_response += text
                        yield sse_data({'text': text})
                    elif event.type == 'message_delta':
                        if hasattr(event, 'usage') and event.usage:
                            output_tokens = getattr(event.usage, 'output_tokens', 0)
                    elif event.type == 'message_start':
                        if hasattr(event, 'message') and hasattr(event.message, 'usage'):
                            input_tokens = getattr(event.message.usage, 'input_tokens', 0)

        # Done event with token usage
        yield sse_event('done', {
            'full_text': full_response,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
        })

    except anthropic.RateLimitError:
        yield sse_error('rate_limited', 'Claude API rate limit reached. Please wait a moment.')
    except anthropic.APIConnectionError:
        yield sse_error('api_error', 'Could not connect to Claude API. Check your connection.')
    except anthropic.APIStatusError as e:
        yield sse_error('api_error', f'Claude API error: {e.status_code}')
    except Exception as e:
        yield sse_error('api_error', f'Unexpected error: {type(e).__name__}')


def sse_data(data):
    """Format a data-only SSE message."""
    return f"data: {json.dumps(data)}\n\n"


def sse_event(event_type, data):
    """Format a named SSE event."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def sse_error(error_type, message):
    """Format an SSE error event."""
    return f"event: error\ndata: {json.dumps({'type': error_type, 'message': message})}\n\n"
