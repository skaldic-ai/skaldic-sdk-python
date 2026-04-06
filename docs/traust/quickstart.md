# Quickstart

## Install

```bash
pip install skaldic-sdk
```

## Connect an agent

Traust sits between your agent and every tool it calls. The agent declares its
intent upfront; the gateway issues a scoped capability token and enforces it on
every subsequent tool call.

### 1. Describe the task

```python
from skaldic.traust import TaskManifest, User

manifest = TaskManifest(
    task_type="summarise_document",
    agent_id="agent-summariser-v1",
    delegating_user_id="user-123",
    requested_tools=["read_document", "call_llm"],
    requested_resources=[{"type": "document", "id": "doc_abc"}],
)
user = User(id="user-123", roles=["analyst"], data_scope="own")
```

- `task_type` must match a task type registered in your gateway's policy store.
- `requested_tools` is an allowlist — calls to tools not listed here are denied
  before they reach the tool.
- Agent permissions are always bounded by the delegating user's permissions.

### 2. Open a session

```python
from skaldic.traust import AgentSession

session = await AgentSession.open(
    gateway_url="http://localhost:8000",
    api_key="your-api-key",
    manifest=manifest,
    user=user,
)
```

If the policy engine denies the manifest, `SessionDeniedError` is raised here —
before the agent does any work.

### 3. Make tool calls

```python
doc = await session.call("read_document", "read", {"id": "doc_abc"})
```

Every call is validated against the capability token and recorded in the audit
log. The agent never holds credentials and never calls tools directly.

### 4. Use as a context manager (recommended)

```python
async with await AgentSession.open(...) as session:
    doc = await session.call("read_document", "read", {"id": "doc_abc"})
    summary = await session.call("call_llm", "complete", {
        "prompt": f"Summarise: {doc}",
    })
```

The session closes automatically on exit. Sessions also expire naturally when
their TTL elapses.

## Handle denials

Denials surface as typed exceptions — catch only what you need:

```python
from skaldic.traust import (
    SessionDeniedError,
    ToolDeniedError,
    EscalationPendingError,
    SessionExpiredError,
    GatewayError,
)

try:
    async with await AgentSession.open(...) as session:
        result = await session.call("read_document", "read", {"id": "doc_abc"})
except SessionDeniedError as e:
    # Policy rejected the session — log and stop
    print(f"denied: {e.reason} (policy {e.policy_version})")
except ToolDeniedError as e:
    # This call was blocked, but the session is still active
    print(f"tool blocked: {e.reason} (audit {e.audit_id})")
except EscalationPendingError as e:
    # Session suspended — wait for operator review
    print(f"escalated: {e.escalation_id}")
except SessionExpiredError:
    # Token expired — open a new session to continue
    ...
except GatewayError as e:
    print(f"gateway {e.status_code}: {e.detail}")
```

See [Exceptions](exceptions.md) for the full hierarchy and guidance on each case.
