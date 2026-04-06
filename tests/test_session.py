"""Tests for AgentSession — all HTTP calls are replaced with a fake HttpClient."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from skaldic.traust import (
    AgentSession,
    EscalationPendingError,
    GatewayError,
    SessionDeniedError,
    SessionExpiredError,
    TaskManifest,
    ToolDeniedError,
    User,
)
from skaldic.traust.http_client import HttpClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GATEWAY = "http://gateway:8000"
API_KEY = "test-key"

MANIFEST = TaskManifest(
    task_type="summarize-customer-report",
    agent_id="agent-test",
    delegating_user_id="usr_abc",
    requested_tools=["read_document"],
    ttl_requested_seconds=300,
)

USER = User(id="usr_abc", roles=["analyst"], data_scope="own")

SESSION_OPEN_ALLOW = {
    "allowed": True,
    "token": "eyJhbGc.fake.token",
    "session_id": "sess_abc123",
    "expires_at": "2026-04-04T10:19:02Z",
}

SESSION_OPEN_DENY = {
    "allowed": False,
    "reason": "task-type-not-permitted",
    "policy_version": "abc1234",
}


def _fake_response(status_code: int, body: Any) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=body)
    resp.text = json.dumps(body)
    return resp


def _fake_http(*responses) -> HttpClient:
    """Return a fake HttpClient whose post() returns the given responses in order."""
    http = MagicMock(spec=HttpClient)
    http.post = AsyncMock(side_effect=list(responses))
    return http


def _open_session(http: HttpClient) -> AgentSession:
    """Return an AgentSession without going through open() — for call() tests."""
    return AgentSession(
        gateway_url=GATEWAY,
        api_key=API_KEY,
        session_id="sess_abc123",
        token="eyJhbGc.fake.token",
        http_client=http,
    )


# ---------------------------------------------------------------------------
# AgentSession.open()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_success():
    http = _fake_http(_fake_response(200, SESSION_OPEN_ALLOW))
    session = await AgentSession.open(GATEWAY, API_KEY, MANIFEST, USER, http_client=http)

    assert isinstance(session, AgentSession)
    assert session._session_id == "sess_abc123"
    assert session._token == "eyJhbGc.fake.token"


@pytest.mark.asyncio
async def test_open_posts_to_session_endpoint():
    http = _fake_http(_fake_response(200, SESSION_OPEN_ALLOW))
    await AgentSession.open(GATEWAY, API_KEY, MANIFEST, USER, http_client=http)

    http.post.assert_called_once()
    url = http.post.call_args[0][0]
    assert url == f"{GATEWAY}/session"


@pytest.mark.asyncio
async def test_open_sends_api_key_header():
    http = _fake_http(_fake_response(200, SESSION_OPEN_ALLOW))
    await AgentSession.open(GATEWAY, API_KEY, MANIFEST, USER, http_client=http)

    headers = http.post.call_args[1].get("headers") or http.post.call_args[0][1]
    assert headers["X-API-Key"] == API_KEY


@pytest.mark.asyncio
async def test_open_raises_session_denied_error():
    http = _fake_http(_fake_response(200, SESSION_OPEN_DENY))

    with pytest.raises(SessionDeniedError) as exc_info:
        await AgentSession.open(GATEWAY, API_KEY, MANIFEST, USER, http_client=http)

    assert exc_info.value.reason == "task-type-not-permitted"
    assert exc_info.value.policy_version == "abc1234"


@pytest.mark.asyncio
async def test_open_raises_gateway_error_on_401():
    http = _fake_http(_fake_response(401, {"detail": "invalid-api-key"}))

    with pytest.raises(GatewayError) as exc_info:
        await AgentSession.open(GATEWAY, API_KEY, MANIFEST, USER, http_client=http)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_open_raises_gateway_error_on_503():
    http = _fake_http(_fake_response(503, {"detail": "policy-engine-unavailable"}))

    with pytest.raises(GatewayError) as exc_info:
        await AgentSession.open(GATEWAY, API_KEY, MANIFEST, USER, http_client=http)

    assert exc_info.value.status_code == 503
    assert "policy-engine-unavailable" in exc_info.value.detail


# ---------------------------------------------------------------------------
# AgentSession.call()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_success_returns_data():
    http = _fake_http(_fake_response(200, {
        "success": True,
        "data": {"title": "Q3 Report", "body": "..."},
        "audit_id": "evt_abc",
        "denial_reason": None,
        "escalation_id": None,
    }))
    session = _open_session(http)

    result = await session.call("read_document", "read", {"id": "doc_abc"})

    assert result["title"] == "Q3 Report"


@pytest.mark.asyncio
async def test_call_posts_correct_payload():
    http = _fake_http(_fake_response(200, {
        "success": True, "data": {}, "audit_id": "evt_abc",
        "denial_reason": None, "escalation_id": None,
    }))
    session = _open_session(http)

    await session.call("read_document", "read", {"id": "doc_abc"})

    payload = http.post.call_args[1].get("json") or http.post.call_args[0][2]
    assert payload["tool"] == "read_document"
    assert payload["operation"] == "read"
    assert payload["session_id"] == "sess_abc123"
    assert payload["capability_token"] == "eyJhbGc.fake.token"


@pytest.mark.asyncio
async def test_call_raises_tool_denied_error():
    http = _fake_http(_fake_response(200, {
        "success": False,
        "data": None,
        "audit_id": "evt_abc",
        "denial_reason": "tool_not_permitted: database",
        "escalation_id": None,
    }))
    session = _open_session(http)

    with pytest.raises(ToolDeniedError) as exc_info:
        await session.call("database", "query", {})

    assert exc_info.value.reason == "tool_not_permitted: database"
    assert exc_info.value.audit_id == "evt_abc"


@pytest.mark.asyncio
async def test_call_raises_escalation_pending_error():
    http = _fake_http(_fake_response(200, {
        "success": False,
        "data": None,
        "audit_id": "evt_abc",
        "denial_reason": "escalated: scope_drift_detected",
        "escalation_id": "esc_xyz789",
    }))
    session = _open_session(http)

    with pytest.raises(EscalationPendingError) as exc_info:
        await session.call("read_document", "read", {})

    assert exc_info.value.escalation_id == "esc_xyz789"
    assert exc_info.value.audit_id == "evt_abc"


@pytest.mark.asyncio
async def test_call_raises_session_expired_on_expired_token():
    http = _fake_http(_fake_response(200, {
        "success": False,
        "data": None,
        "audit_id": "evt_abc",
        "denial_reason": "token_expired",
        "escalation_id": None,
    }))
    session = _open_session(http)

    with pytest.raises(SessionExpiredError):
        await session.call("read_document", "read", {})


@pytest.mark.asyncio
async def test_call_raises_session_expired_on_revoked():
    http = _fake_http(_fake_response(200, {
        "success": False,
        "data": None,
        "audit_id": "evt_abc",
        "denial_reason": "session_revoked",
        "escalation_id": None,
    }))
    session = _open_session(http)

    with pytest.raises(SessionExpiredError):
        await session.call("read_document", "read", {})


@pytest.mark.asyncio
async def test_call_raises_gateway_error_on_http_error():
    http = _fake_http(_fake_response(429, {"detail": "rate-limit-exceeded"}))
    session = _open_session(http)

    with pytest.raises(GatewayError) as exc_info:
        await session.call("read_document", "read", {})

    assert exc_info.value.status_code == 429


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_context_manager():
    http = _fake_http(
        _fake_response(200, SESSION_OPEN_ALLOW),
        _fake_response(200, {
            "success": True, "data": {"ok": True}, "audit_id": "evt_abc",
            "denial_reason": None, "escalation_id": None,
        }),
    )

    async with await AgentSession.open(GATEWAY, API_KEY, MANIFEST, USER, http_client=http) as session:
        result = await session.call("read_document", "read", {"id": "doc_abc"})

    assert result["ok"] is True


# ---------------------------------------------------------------------------
# close() is a no-op
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_is_noop():
    http = _fake_http()
    session = _open_session(http)
    await session.close()  # must not raise
    http.post.assert_not_called()
