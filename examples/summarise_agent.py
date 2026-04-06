"""Example agent using the Skaldic Traust SDK.

Demonstrates opening a session, making tool calls, and handling typed exceptions.

Usage (with the Traust stack running):

    pip install skaldic-sdk
    python examples/summarise_agent.py

Environment variables:

    GATEWAY_URL  — default: http://localhost:8000
    API_KEY      — default: dev-key-change-me
"""

import asyncio
import os

from skaldic.traust import (
    AgentSession,
    EscalationPendingError,
    GatewayError,
    SessionDeniedError,
    SessionExpiredError,
    TaskManifest,
    ToolDeniedError,
    User,
)

GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8000")
API_KEY = os.environ.get("API_KEY", "dev-key-change-me")


async def main() -> None:
    manifest = TaskManifest(
        task_type="summarize-customer-report",
        agent_id="agent-summariser-v2",
        delegating_user_id="usr_9f2a",
        requested_resources=[{"type": "document", "id": "doc_abc123"}],
        requested_tools=["read_document", "call_llm"],
        ttl_requested_seconds=300,
    )
    user = User(id="usr_9f2a", roles=["analyst"], data_scope="own")

    print(f"Opening session at {GATEWAY_URL} ...")

    try:
        session = await AgentSession.open(
            gateway_url=GATEWAY_URL,
            api_key=API_KEY,
            manifest=manifest,
            user=user,
        )
    except SessionDeniedError as e:
        print(f"Session denied: {e.reason} (policy: {e.policy_version})")
        return
    except GatewayError as e:
        print(f"Gateway error {e.status_code}: {e.detail}")
        return

    print(f"Session opened: {session._session_id}")

    async with session:
        # Read a document
        try:
            doc = await session.call("read_document", "read", {"id": "doc_abc123"})
            print(f"Document: {doc}")
        except ToolDeniedError as e:
            print(f"Tool denied: {e.reason} (audit: {e.audit_id})")
        except EscalationPendingError as e:
            print(f"Session escalated for review: {e.escalation_id}")
            return
        except SessionExpiredError:
            print("Session expired — open a new session to continue")
            return

        # Summarise with LLM
        try:
            summary = await session.call("call_llm", "complete", {
                "prompt": f"Summarise this document: {doc}",
            })
            print(f"Summary: {summary}")
        except ToolDeniedError as e:
            print(f"Tool denied: {e.reason}")


if __name__ == "__main__":
    asyncio.run(main())
