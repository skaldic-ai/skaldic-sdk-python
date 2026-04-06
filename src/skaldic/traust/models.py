"""Public data models for Skaldic Traust."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TaskManifest(BaseModel):
    """Describes the intent of an agent task session.

    The gateway evaluates this declaration against the active policy to decide
    whether to issue a capability token for the session.
    """

    task_type: str
    """Logical identifier for the kind of work being performed (e.g. ``"summarise_document"``)."""

    agent_id: str
    """Registered identifier of the agent opening the session."""

    delegating_user_id: str
    """Identity of the human user on whose behalf the agent is acting."""

    requested_tools: list[str] = Field(default_factory=list)
    """Tool names the agent expects to call during this session."""

    requested_resources: list[dict[str, Any]] = Field(default_factory=list)
    """Resources the agent expects to access (e.g. ``[{"type": "document", "id": "doc_123"}]``)."""

    ttl_requested_seconds: int = 300
    """How long the session token should be valid, in seconds."""


class User(BaseModel):
    """The human user delegating authority to the agent."""

    id: str
    """Unique user identifier."""

    roles: list[str] = Field(default_factory=list)
    """Roles assigned to the user in the operator's system."""

    data_scope: str = "own"
    """Data visibility scope (e.g. ``"own"``, ``"team"``, ``"all"``)."""
