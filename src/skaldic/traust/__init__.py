"""Skaldic Traust — Task-Based Access Control (TBAC) for AI agents.

Traust sits between an AI agent and every tool it can call. Before a session
starts the agent declares its intent via a :class:`TaskManifest`; the gateway
evaluates that declaration and issues a scoped capability token. Every
subsequent tool call is validated against the token — the agent can never
exceed the permissions of the user it acts on behalf of.

Quickstart
----------
::

    from skaldic.traust import AgentSession, TaskManifest, User

    manifest = TaskManifest(
        task_type="summarise_document",
        agent_id="agent-summariser-v1",
        delegating_user_id="user-123",
        requested_tools=["read_document", "call_llm"],
    )
    user = User(id="user-123", roles=["analyst"])

    async with await AgentSession.open(
        gateway_url="http://localhost:8000",
        api_key="your-api-key",
        manifest=manifest,
        user=user,
    ) as session:
        result = await session.call("read_document", "read", {"id": "doc_abc"})

Exported names
--------------
- :class:`AgentSession` — the primary entry point
- :class:`TaskManifest`, :class:`User` — request models
- :exc:`TraustError`, :exc:`SessionDeniedError`, :exc:`ToolDeniedError`,
  :exc:`EscalationPendingError`, :exc:`SessionExpiredError`,
  :exc:`GatewayError` — exception hierarchy
"""

from .exceptions import (
    EscalationPendingError,
    GatewayError,
    SessionDeniedError,
    SessionExpiredError,
    ToolDeniedError,
    TraustError,
)
from .models import TaskManifest, User
from .session import AgentSession

__all__ = [
    # Session
    "AgentSession",
    # Models
    "TaskManifest",
    "User",
    # Exceptions
    "TraustError",
    "SessionDeniedError",
    "ToolDeniedError",
    "SessionExpiredError",
    "EscalationPendingError",
    "GatewayError",
]
