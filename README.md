# skaldic-sdk

Python SDK for [Skaldic AI](https://skaldic.ai)

## Installation

```bash
pip install skaldic-sdk
```

## Components

| Package | Status | Description |
|---|---|---|
| `skaldic.traust` | Available | Task-Based Access Control (TBAC) for AI agents |
| `skaldic.odin` | Coming soon | — |
| `skaldic.huginn` | Coming soon | — |
| `skaldic.muninn` | Coming soon | — |
| `skaldic.runes` | Coming soon | — |

## Quick start — Traust

Traust enforces task-scoped, policy-driven access control for AI agents. The agent declares its intent upfront; the gateway issues a capability token and audits every tool call against it.

```python
from skaldic.traust import AgentSession, TaskManifest, User

manifest = TaskManifest(
    task_type="summarise_document",
    agent_id="agent-summariser-v1",
    delegating_user_id="user-123",
    requested_tools=["read_document", "call_llm"],
    requested_resources=[{"type": "document", "id": "doc_abc"}],
)
user = User(id="user-123", roles=["analyst"], data_scope="own")

async with await AgentSession.open(
    gateway_url="http://localhost:8000",
    api_key="your-api-key",
    manifest=manifest,
    user=user,
) as session:
    result = await session.call("read_document", "read", {"id": "doc_abc"})
```

Denials surface as typed exceptions — `SessionDeniedError`, `ToolDeniedError`, `EscalationPendingError`, `SessionExpiredError`, `GatewayError`.

## License

Apache 2.0
