"""Exception hierarchy for Skaldic Traust."""


class TraustError(Exception):
    """Base class for all Skaldic Traust errors."""


class SessionDeniedError(TraustError):
    """Raised by ``AgentSession.open()`` when the policy engine denies the task session."""

    def __init__(self, reason: str, policy_version: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.policy_version = policy_version


class ToolDeniedError(TraustError):
    """Raised by ``AgentSession.call()`` when the tool call is denied by policy or guardrails."""

    def __init__(self, reason: str, audit_id: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.audit_id = audit_id


class EscalationPendingError(TraustError):
    """Raised by ``AgentSession.call()`` when a guardrail escalation has suspended the session.

    The session is suspended pending operator review. The agent should stop and
    wait or notify the user — it cannot make further tool calls until the
    escalation is resolved.
    """

    def __init__(self, escalation_id: str, audit_id: str) -> None:
        super().__init__(f"session suspended pending escalation review: {escalation_id}")
        self.escalation_id = escalation_id
        self.audit_id = audit_id


class SessionExpiredError(TraustError):
    """Raised by ``AgentSession.call()`` when the capability token has expired or been revoked.

    Open a new session via ``AgentSession.open()`` to continue.
    """


class GatewayError(TraustError):
    """Raised when the gateway returns an unexpected HTTP error (4xx/5xx)."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"gateway error {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail
