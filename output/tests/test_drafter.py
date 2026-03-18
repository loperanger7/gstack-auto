"""Tests for drafter.py — Claude drafting with mocked API."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

import drafter


def _mock_claude_response(text: str):
    """Create a mock Claude API response."""
    mock_client = AsyncMock()
    resp = MagicMock()
    resp.content = [MagicMock(text=text)]
    mock_client.messages.create = AsyncMock(return_value=resp)
    return mock_client


@pytest.mark.asyncio
async def test_draft_variants_returns_list():
    variants_json = json.dumps([
        {"label": "A", "text": "Great question! gstack-auto makes it easy."},
        {"label": "B", "text": "Check out gstack-auto for that."},
    ])
    client = _mock_claude_response(variants_json)
    result = await drafter.draft_variants(
        client, "What is gstack?", "Alice", "alice", "question"
    )
    assert len(result) == 2
    assert result[0]["label"] == "A"
    assert result[1]["label"] == "B"


@pytest.mark.asyncio
async def test_variants_under_280_chars():
    variants_json = json.dumps([
        {"label": "A", "text": "Short reply."},
        {"label": "B", "text": "x" * 300},  # Over 280
    ])
    client = _mock_claude_response(variants_json)
    result = await drafter.draft_variants(
        client, "test", "Bob", "bob", "neutral"
    )
    assert len(result) == 1  # Only the short one survives
    assert result[0]["label"] == "A"


@pytest.mark.asyncio
async def test_sentiment_classification():
    client = _mock_claude_response("praise")
    result = await drafter.classify_sentiment(client, "gstack is the best!")
    assert result == "praise"


@pytest.mark.asyncio
async def test_sentiment_invalid_defaults_neutral():
    client = _mock_claude_response("excited")
    result = await drafter.classify_sentiment(client, "wow gstack")
    assert result == "neutral"


@pytest.mark.asyncio
async def test_xml_escaping():
    """Tweet text with angle brackets doesn't break the prompt."""
    variants_json = json.dumps([
        {"label": "A", "text": "Nice try with the script tag."},
    ])
    client = _mock_claude_response(variants_json)
    result = await drafter.draft_variants(
        client, '<script>alert("xss")</script> gstack rocks',
        "Hacker", "hacker", "neutral"
    )
    assert len(result) == 1
    # Verify the prompt contained escaped text
    call_args = client.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "<script>" not in prompt
    assert "&lt;script&gt;" in prompt


@pytest.mark.asyncio
async def test_claude_refusal_handled():
    import anthropic
    client = AsyncMock()
    client.messages.create = AsyncMock(
        side_effect=anthropic.APIStatusError(
            message="content refused",
            response=MagicMock(status_code=400),
            body={"error": {"message": "content refused"}},
        )
    )
    result = await drafter.draft_variants(
        client, "offensive content", "Bad", "bad", "criticism"
    )
    assert result == []


@pytest.mark.asyncio
async def test_claude_timeout_retries():
    import anthropic
    client = AsyncMock()
    client.messages.create = AsyncMock(
        side_effect=anthropic.APITimeoutError(request=MagicMock())
    )
    result = await drafter.draft_variants(
        client, "test", "A", "a", "neutral", retries=2
    )
    assert result == []
    assert client.messages.create.call_count == 3  # 1 + 2 retries


@pytest.mark.asyncio
async def test_parse_markdown_code_fence():
    """Claude sometimes wraps JSON in markdown code fences."""
    fenced = '```json\n[{"label": "A", "text": "Hello!"}]\n```'
    client = _mock_claude_response(fenced)
    result = await drafter.draft_variants(
        client, "test", "A", "a", "neutral"
    )
    assert len(result) == 1
    assert result[0]["text"] == "Hello!"


@pytest.mark.asyncio
async def test_draft_with_thread_context():
    variants_json = json.dumps([
        {"label": "A", "text": "Great thread!"},
    ])
    client = _mock_claude_response(variants_json)
    thread = [{"text": "I was talking about gstack..."}, {"text": "It's great"}]
    result = await drafter.draft_variants(
        client, "gstack is cool", "Alice", "alice", "praise", thread=thread
    )
    assert len(result) == 1
    prompt = client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "I was talking about gstack" in prompt
