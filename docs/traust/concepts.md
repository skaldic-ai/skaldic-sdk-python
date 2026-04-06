# Concepts

## Why RBAC breaks for agents

Role-Based Access Control works for humans. A user has a role; the role has
permissions; the user gets access. Simple.

Agents break this model. The same agent, with the same credentials, might
summarise a customer report in one task and browse the web for competitive
research in the next. Granting it a role that covers both means it always has
more access than it needs. Agents are fast, autonomous, and can be manipulated
through the content they process — a static role is not enough.

## Task-Based Access Control (TBAC)

Traust replaces static roles with task sessions.

Before executing anything, an agent declares its intent: what task it is
performing, on whose behalf, and what resources it expects to need. The system
evaluates that declaration and issues a **scoped capability token** valid only
for that session. When the task ends, the token expires. The agent goes back
to having nothing.

**Core invariant:** agent permissions are always a strict subset of the
delegating user's permissions, further narrowed by the task type.

## Sessions

A session is opened by calling `AgentSession.open` with a `TaskManifest` and
a `User`. The gateway evaluates the manifest against the active policy and
either issues a token or raises `SessionDeniedError`.

Each session is independent — permissions do not accumulate across sessions.
An agent running ten tasks in parallel has ten separate tokens, each scoped
to its own task.

Sessions expire via their TTL (requested in `TaskManifest.ttl_requested_seconds`,
subject to policy limits). They can also be revoked early by an operator.

## Guardrail pipeline

Every tool call passes through a sequential guardrail pipeline inside the
gateway before execution and after:

| Stage | Phase | What it checks |
|---|---|---|
| Schema | Pre-execution | Is the request structurally valid? |
| Rate | Pre-execution | Is call frequency within the task envelope? |
| Scope | Pre-execution | Does this action match the declared manifest? |
| Injection | Pre-execution | Are there adversarial instructions in the parameters? |
| Content | Post-execution | Does the output contain PII or sensitive data? |
| Drift | Post-execution | Is the session profile diverging from the declared manifest? |

Guardrail violations either deny the specific call (`ToolDeniedError`) or
suspend the entire session pending operator review (`EscalationPendingError`).

## Escalations

When a guardrail escalates, the session is suspended. No further tool calls
can be made until an operator approves or rejects the escalation via the
Traust dashboard.

On `EscalationPendingError`, the agent should stop and surface the situation
to the user or orchestrator. The `escalation_id` on the exception can be used
to reference the pending review.

## Hard boundaries

These are non-negotiable in the Traust design:

- **Agents never call tools directly.** The gateway is the only path to execution.
- **Agents never hold credentials.** Secrets are injected just-in-time by the vault.
- **Permissions are never additive across sessions.** Each task starts from zero.
- **Deny by default.** Nothing is permitted unless explicitly granted by policy.
- **The agent cannot see the enforcement.** Parameter rewriting and output
  filtering happen transparently.
