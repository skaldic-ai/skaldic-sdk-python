"""Thin async HTTP client wrapper used by AgentSession.

Injectable for testing — pass a subclass or mock to :meth:`AgentSession.open`
to avoid real network calls::

    class FakeHttpClient(HttpClient):
        async def post(self, url, headers, json):
            return fake_response(200, {...})
"""

from typing import Any

import httpx


class HttpClient:
    """Wraps ``httpx.AsyncClient`` for gateway communication.

    Creates a new ``httpx.AsyncClient`` per request (stateless). Subclass or
    replace entirely in tests to avoid real network calls.

    Args:
        timeout: Request timeout in seconds. Applies to both the connection
            and the read phase. Defaults to ``30.0``.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self._timeout = timeout

    async def post(self, url: str, headers: dict[str, str], json: Any) -> httpx.Response:
        """Send an HTTP POST request and return the response.

        Args:
            url: Full URL to POST to.
            headers: HTTP headers to include in the request.
            json: Request body, serialised as JSON.

        Returns:
            The :class:`httpx.Response`. The caller is responsible for
            checking the status code.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await client.post(url, headers=headers, json=json)
