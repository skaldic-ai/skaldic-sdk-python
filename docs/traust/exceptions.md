# Exceptions

All exceptions raised by the Traust SDK are subclasses of `TraustError`.

```
TraustError
├── SessionDeniedError
├── ToolDeniedError
├── EscalationPendingError
├── SessionExpiredError
└── GatewayError
```

## TraustError

Base class. Catch this to handle any SDK error without caring about the
specific type.

## SessionDeniedError

Raised by `AgentSession.open` when the policy engine rejects the manifest.

The agent cannot proceed — the declared task type, agent, or user combination
was not permitted by the active policy. No capability token was issued.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `reason` | `str` | Machine-readable denial reason (e.g. `"task-type-not-permitted"`) |
| `policy_version` | `str` | Policy version (git commit hash) that produced this decision |

**What to do:** Log the reason and policy version. Do not retry without
changing the manifest or updating the policy.

## ToolDeniedError

Raised by `AgentSession.call` when a specific tool call is blocked.

The session itself remains active. The agent can inspect the denial reason,
inform the user or orchestrator, and continue with other tool calls.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `reason` | `str` | Machine-readable denial reason (e.g. `"tool_not_permitted: database"`) |
| `audit_id` | `str` | Audit log event ID for this denial |

**What to do:** Log the denial, surface it to the user if appropriate, and
continue the session with other calls.

## EscalationPendingError

Raised by `AgentSession.call` when a guardrail escalation suspends the session.

A guardrail (scope drift, injection detection, etc.) flagged the call. The
session is now suspended — no further tool calls can be made until an operator
approves or rejects the escalation via the Traust dashboard.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `escalation_id` | `str` | ID of the escalation record in the operator review queue |
| `audit_id` | `str` | Audit log event ID that triggered the escalation |

**What to do:** Stop immediately. Surface the situation to the user. Wait for
the escalation to be resolved out of band.

## SessionExpiredError

Raised by `AgentSession.call` when the capability token is no longer valid.

This happens when the token's TTL has elapsed or an operator has explicitly
revoked the session.

**What to do:** Call `AgentSession.open` to open a fresh session, then retry.

## GatewayError

Raised when the gateway returns an unexpected HTTP error (4xx/5xx).

This indicates an infrastructure problem rather than a policy decision —
invalid API key (`401`), rate limit (`429`), gateway unavailable (`503`), etc.

**Attributes:**

| Attribute | Type | Description |
|---|---|---|
| `status_code` | `int` | HTTP status code |
| `detail` | `str` | Error detail from the response body |

**What to do:** On `5xx`, retry with backoff. On `401`, check your API key.
On `429`, back off and reduce call frequency.
