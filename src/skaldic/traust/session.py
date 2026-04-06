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

    Do not construct directly — use the :meth:`open` classmethod::

        async with await AgentSession.open(
            gateway_url="http://localhost:8000",
            api_key="...",
            manifest=manifest,
            user=user,
        ) as session:
            result = await session.call("read_document", "read", {"id": "doc_123"})
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

        Args:
            gateway_url: Base URL of the Traust gateway (e.g. ``"http://localhost:8000"``).
            api_key: API key issued by the gateway operator.
            manifest: Declares the task intent — type, agent, user, requested tools/resources.
            user: The human user the agent is acting on behalf of.
            http_client: Optional custom HTTP client (primarily for testing).

        Returns:
            An :class:`AgentSession` ready to make tool calls.

        Raises:
            SessionDeniedError: The policy engine denied the session.
            GatewayError: Unexpected HTTP error from the gateway.
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
        """Make a tool call through the gateway.

        Args:
            tool: Name of the tool to invoke (must be in the session manifest's ``requested_tools``).
            operation: Operation to perform on the tool (e.g. ``"read"``, ``"write"``).
            params: Tool-specific parameters.

        Returns:
            The tool result as a dict on success.

        Raises:
            ToolDeniedError: Tool call was denied by policy or guardrails.
            EscalationPendingError: A guardrail escalation suspended the session.
            SessionExpiredError: The session token has expired or been revoked.
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
        """Close the session. Sessions expire naturally via their TTL."""

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
