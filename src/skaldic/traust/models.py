"""Request models for Skaldic Traust.

These models are passed to :meth:`AgentSession.open` and describe the agent's
declared intent for a task session. The gateway evaluates them against the
active policy before issuing a capability token.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskManifest(BaseModel):
    """Declares the intent of an agent task session.

    The gateway evaluates this manifest against the active policy to decide
    whether to issue a capability token. Permissions granted are always a
    strict subset of the delegating user's permissions, further narrowed by
    the task type.

    All fields are included in the audit log for every session.

    Example:
        ::

            manifest = TaskManifest(
                task_type="summarise_document",
                agent_id="agent-summariser-v1",
                delegating_user_id="user-123",
                requested_tools=["read_document", "call_llm"],
                requested_resources=[{"type": "document", "id": "doc_abc"}],
                ttl_requested_seconds=300,
            )

    Attributes:
        task_type: Logical identifier for the kind of work being performed.
            Must match a task type registered in the gateway's policy store
            (e.g. ``"summarise_document"``, ``"web_research"``).
        agent_id: Registered identifier of the agent opening the session.
            Used for rate limiting, audit logging, and trust-tier lookup.
        delegating_user_id: Identity of the human user on whose behalf the
            agent is acting. Agent permissions are always bounded by this
            user's permissions — the agent can never exceed them.
        requested_tools: Names of the tools the agent expects to call during
            this session (e.g. ``["read_document", "call_llm"]``). Calls to
            tools not listed here will be denied by the gateway.
        requested_resources: Resources the agent expects to access, expressed
            as a list of dicts with at least a ``"type"`` and ``"id"`` key
            (e.g. ``[{"type": "document", "id": "doc_abc"}]``). Used by
            the policy engine to scope data access.
        ttl_requested_seconds: Requested lifetime of the capability token in
            seconds. The gateway may issue a shorter TTL based on policy.
            Defaults to ``300`` (5 minutes).
    """

    task_type: str
    agent_id: str
    delegating_user_id: str
    requested_tools: list[str] = Field(default_factory=list)
    requested_resources: list[dict[str, Any]] = Field(default_factory=list)
    ttl_requested_seconds: int = 300


class User(BaseModel):
    """Represents the human user delegating authority to the agent.

    The gateway uses this to look up the user's permissions in the policy
    store and ensure the agent never acts beyond what the user is allowed
    to do themselves.

    Example:
        ::

            user = User(id="user-123", roles=["analyst"], data_scope="own")

    Attributes:
        id: Unique identifier for the user in the operator's system.
        roles: Roles assigned to the user (e.g. ``["analyst"]``,
            ``["admin"]``). The policy engine uses these to determine
            what the user — and therefore the agent — is permitted to do.
        data_scope: Controls which data the user (and agent) can access.
            Common values:

            - ``"own"`` — only data belonging to this user (default)
            - ``"team"`` — data visible to the user's team
            - ``"all"`` — unrestricted data access (typically admin-only)
    """

    id: str
    roles: list[str] = Field(default_factory=list)
    data_scope: str = "own"
