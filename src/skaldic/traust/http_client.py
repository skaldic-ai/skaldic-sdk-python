"""Thin async HTTP client wrapper used by AgentSession.

Injectable for testing — pass a subclass or mock to ``AgentSession.open()``.
"""

from typing import Any

import httpx


class HttpClient:
    """Wraps ``httpx.AsyncClient`` for gateway communication.

    Creates a new httpx client per request (stateless). Subclass or replace
    in tests to avoid real network calls.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def post(self, url: str, headers: dict[str, str], json: Any) -> httpx.Response:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.post(url, headers=headers, json=json)
