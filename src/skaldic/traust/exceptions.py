"""Exception hierarchy for Skaldic Traust.

All exceptions raised by the SDK are subclasses of :exc:`TraustError`, so a
single ``except TraustError`` can catch everything if you prefer not to handle
each case individually.

Typical handling pattern::

    try:
        async with await AgentSession.open(...) as session:
            result = await session.call("read_document", "read", {"id": "doc_abc"})
    except SessionDeniedError as e:
        # Policy rejected the session before it started
        print(f"denied: {e.reason} (policy {e.policy_version})")
    except ToolDeniedError as e:
        # A specific tool call was blocked — session is still active
        print(f"tool blocked: {e.reason} (audit {e.audit_id})")
    except EscalationPendingError as e:
        # Session suspended; operator review required before continuing
        print(f"escalated: {e.escalation_id}")
    except SessionExpiredError:
        # Token expired or revoked — open a new session to continue
        ...
    except GatewayError as e:
        # Unexpected HTTP error from the gateway
        print(f"gateway {e.status_code}: {e.detail}")
"""


class TraustError(Exception):
    """Base class for all Skaldic Traust SDK errors.

    Catch this to handle any SDK error without caring about the specific type.
    """


class SessionDeniedError(TraustError):
    """Raised by :meth:`AgentSession.open` when the policy engine denies the session.

    This means the declared :class:`TaskManifest` was evaluated and rejected
    before any capability token was issued. The agent cannot proceed with this
    task — the denial reason and policy version are available for logging.

    Attributes:
        reason: Machine-readable denial reason returned by the policy engine
            (e.g. ``"task-type-not-permitted"``, ``"agent-not-registered"``).
        policy_version: Version identifier (git commit hash) of the policy
            that produced this decision. Useful for auditing and debugging.
    """

    def __init__(self, reason: str, policy_version: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.policy_version = policy_version


class ToolDeniedError(TraustError):
    """Raised by :meth:`AgentSession.call` when a tool call is denied.

    The session itself remains active — only this specific tool call was
    blocked. The agent can inspect the denial reason, inform the user or
    orchestrator, and continue with other tool calls if appropriate.

    Attributes:
        reason: Machine-readable denial reason (e.g.
            ``"tool_not_permitted: database"``,
            ``"resource_out_of_scope"``).
        audit_id: Identifier of the audit event recorded for this denial.
            Use this when correlating SDK exceptions with the gateway's
            audit log.
    """

    def __init__(self, reason: str, audit_id: str) -> None:
        super().__init__(reason)
        self.reason = reason
        self.audit_id = audit_id


class EscalationPendingError(TraustError):
    """Raised by :meth:`AgentSession.call` when a guardrail escalation occurs.

    A guardrail (e.g. scope drift, injection detection) flagged this call and
    suspended the session pending operator review. The agent **cannot make
    further tool calls** until an operator approves or rejects the escalation
    via the Traust dashboard.

    On receiving this exception the agent should stop, surface the situation
    to the user or orchestrator, and wait for the escalation to be resolved
    out of band.

    Attributes:
        escalation_id: Unique identifier for the escalation record in the
            operator's review queue. Can be used to poll or reference the
            escalation externally.
        audit_id: Identifier of the audit event that triggered the escalation.
    """

    def __init__(self, escalation_id: str, audit_id: str) -> None:
        super().__init__(f"session suspended pending escalation review: {escalation_id}")
        self.escalation_id = escalation_id
        self.audit_id = audit_id


class SessionExpiredError(TraustError):
    """Raised by :meth:`AgentSession.call` when the capability token is no longer valid.

    This happens when the token's TTL has elapsed or an operator has explicitly
    revoked the session. Call :meth:`AgentSession.open` to open a new session
    and obtain a fresh token before continuing.
    """


class GatewayError(TraustError):
    """Raised when the gateway returns an unexpected HTTP error (4xx/5xx).

    This indicates a problem at the infrastructure level rather than a policy
    decision — for example, an invalid API key (``401``), a rate limit
    (``429``), or a transient gateway unavailability (``503``).

    Attributes:
        status_code: The HTTP status code returned by the gateway.
        detail: Human-readable detail message extracted from the response body.
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"gateway error {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail
