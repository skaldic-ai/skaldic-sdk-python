"""AgentSession — the primary Traust SDK interface."""

from __future__ import annotations

from typing import Any

from .exceptions import (
    EscalationPendingError,
    GatewayError,
    SessionDeniedError,
    SessionExpiredError,
    ToolDeniedError,
)
from .http_client import HttpClient
from .models import TaskManifest, User

# Denial reasons that indicate an expired or revoked session rather than a
# policy decision on this specific tool call.
_EXPIRED_DENIAL_PREFIXES = (
    "session_expired",
    "session_not_found",
    "session_suspended",
    "session_revoked",
    "token_expired",
    "invalid_token",
)


class AgentSession:
    """An active task session with the Traust gateway.

    Manages a scoped capability token for the duration of one agent task.
    Every tool call made through :meth:`call` is validated against that token
    — the agent can only use the tools and resources declared in the manifest
    passed to :meth:`open`.

    Do not construct directly. Use the :meth:`open` classmethod, which
    contacts the gateway, evaluates the manifest against the active policy,
    and returns an initialised session::

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

    The session can be used as an async context manager (recommended) or
    managed manually via :meth:`close`.

    Attributes:
        session_id: Read-only identifier assigned by the gateway when the
            session was opened. Appears in all audit log entries for this
            session.
    """

    def __init__(
        self,
        gateway_url: str,
        api_key: str,
        session_id: str,
        token: str,
        http_client: HttpClient,
    ) -> None:
        self._gateway_url = gateway_url.rstrip("/")
        self._api_key = api_key
        self._session_id = session_id
        self._token = token
        self._http = http_client

    @property
    def session_id(self) -> str:
        """Gateway-assigned session identifier.

        Included in every audit log entry for this session. Use this when
        correlating SDK activity with the Traust audit log or operator
        dashboard.
        """
        return self._session_id

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    async def open(
        cls,
        gateway_url: str,
        api_key: str,
        manifest: TaskManifest,
        user: User,
        http_client: HttpClient | None = None,
    ) -> "AgentSession":
        """Open a task session with the Traust gateway.

        Sends the manifest and user context to the gateway, which evaluates
        them against the active policy. On success, a scoped capability token
        is issued and an :class:`AgentSession` is returned. On denial, a
        :exc:`SessionDeniedError` is raised immediately.

        Args:
            gateway_url: Base URL of the Traust gateway
                (e.g. ``"http://localhost:8000"``).
            api_key: API key issued by the gateway operator.
            manifest: Declares the task intent — type, agent, delegating user,
                requested tools and resources.
            user: The human user the agent is acting on behalf of. Agent
                permissions are always bounded by this user's permissions.
            http_client: Optional custom HTTP client. Pass a subclass or mock
                to avoid real network calls in tests.

        Returns:
            An :class:`AgentSession` ready to make tool calls.

        Raises:
            SessionDeniedError: The policy engine denied the session.
            GatewayError: Unexpected HTTP error from the gateway (e.g. invalid
                API key, gateway unavailable).
        """
        http = http_client or HttpClient()
        url = gateway_url.rstrip("/") + "/session"
        payload = {
            "manifest": manifest.model_dump(),
            "user": user.model_dump(),
        }

        response = await http.post(url, headers={"X-API-Key": api_key}, json=payload)

        if response.status_code != 200:
            detail = _extract_detail(response)
            raise GatewayError(status_code=response.status_code, detail=detail)

        body = response.json()

        if not body.get("allowed", True):
            raise SessionDeniedError(
                reason=body.get("reason", "denied"),
                policy_version=body.get("policy_version", "unknown"),
            )

        return cls(
            gateway_url=gateway_url,
            api_key=api_key,
            session_id=body["session_id"],
            token=body["token"],
            http_client=http,
        )

    # ------------------------------------------------------------------
    # Tool calls
    # ------------------------------------------------------------------

    async def call(
        self,
        tool: str,
        operation: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Make a tool call through the Traust gateway.

        The gateway validates the capability token, runs the configured
        guardrail pipeline (schema, rate, scope, injection checks pre-execution;
        content and drift checks post-execution), executes the tool, and
        returns the result. The entire interaction is recorded in the audit log.

        Args:
            tool: Name of the tool to invoke. Must be listed in the session
                manifest's ``requested_tools`` — calls to unlisted tools are
                denied immediately.
            operation: The operation to perform on the tool
                (e.g. ``"read"``, ``"write"``, ``"complete"``). The available
                operations depend on the tool's registration in the gateway.
            params: Tool-specific parameters passed to the tool. These are
                validated by the guardrail pipeline and may be rewritten by
                the gateway (e.g. to inject data-scope filters) before
                reaching the tool.

        Returns:
            The tool's result as a plain dict. The structure depends on the
            tool — consult the tool's documentation or the gateway's tool
            registry.

        Raises:
            ToolDeniedError: The tool call was denied by policy or a guardrail.
                The session remains active; other tool calls can still be made.
            EscalationPendingError: A guardrail flagged the call and suspended
                the session pending operator review. No further tool calls can
                be made until the escalation is resolved.
            SessionExpiredError: The capability token has expired or been
                revoked. Open a new session via :meth:`open` to continue.
            GatewayError: Unexpected HTTP error from the gateway.
        """
        url = self._gateway_url + "/call"
        payload = {
            "session_id": self._session_id,
            "capability_token": self._token,
            "tool": tool,
            "operation": operation,
            "params": params,
        }

        response = await self._http.post(
            url, headers={"X-API-Key": self._api_key}, json=payload
        )

        if response.status_code != 200:
            detail = _extract_detail(response)
            raise GatewayError(status_code=response.status_code, detail=detail)

        body = response.json()

        if body.get("success"):
            return body.get("data") or {}

        denial_reason: str = body.get("denial_reason") or "denied"
        audit_id: str = body.get("audit_id", "")
        escalation_id: str | None = body.get("escalation_id")

        if escalation_id:
            raise EscalationPendingError(escalation_id=escalation_id, audit_id=audit_id)

        if any(denial_reason.startswith(p) for p in _EXPIRED_DENIAL_PREFIXES):
            raise SessionExpiredError(denial_reason)

        raise ToolDeniedError(reason=denial_reason, audit_id=audit_id)

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def close(self) -> None:
        """Close the session.

        Sessions expire naturally when their TTL elapses. Calling ``close``
        is a clean-up signal and is safe to call multiple times. When using
        the session as an async context manager, ``close`` is called
        automatically on exit.
        """

    async def __aenter__(self) -> "AgentSession":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _extract_detail(response: Any) -> str:
    try:
        return response.json().get("detail", response.text)
    except Exception:
        return response.text
