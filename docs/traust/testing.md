# Testing

## Injecting a fake HTTP client

`AgentSession` accepts an optional `http_client` parameter in `open`. Pass a
subclass or mock of `HttpClient` to avoid real network calls in tests:

```python
from unittest.mock import AsyncMock, MagicMock
from skaldic.traust.http_client import HttpClient

def fake_response(status_code, body):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json = MagicMock(return_value=body)
    resp.text = str(body)
    return resp

http = MagicMock(spec=HttpClient)
http.post = AsyncMock(return_value=fake_response(200, {
    "allowed": True,
    "session_id": "sess_test",
    "token": "fake-token",
}))

session = await AgentSession.open(
    gateway_url="http://gateway",
    api_key="test-key",
    manifest=manifest,
    user=user,
    http_client=http,
)
```

## Testing denial paths

Use `AsyncMock(side_effect=[...])` to feed multiple responses in order — one
for `open` and one per `call`:

```python
http.post = AsyncMock(side_effect=[
    fake_response(200, {"allowed": True, "session_id": "sess_1", "token": "tok"}),
    fake_response(200, {"success": False, "denial_reason": "tool_not_permitted: db",
                        "audit_id": "evt_1", "escalation_id": None}),
])

async with await AgentSession.open(..., http_client=http) as session:
    with pytest.raises(ToolDeniedError) as exc:
        await session.call("db", "query", {})

assert exc.value.reason == "tool_not_permitted: db"
```

## Constructing a session directly

For `call` tests that don't need to exercise `open`, construct `AgentSession`
directly:

```python
from skaldic.traust import AgentSession

session = AgentSession(
    gateway_url="http://gateway",
    api_key="test-key",
    session_id="sess_test",
    token="fake-token",
    http_client=http,
)
```
