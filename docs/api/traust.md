<a id="skaldic.traust.session"></a>

# skaldic.traust.session

AgentSession — the primary Traust SDK interface.

<a id="skaldic.traust.session.annotations"></a>

## annotations

<a id="skaldic.traust.session.Any"></a>

## Any

<a id="skaldic.traust.session.EscalationPendingError"></a>

## EscalationPendingError

<a id="skaldic.traust.session.GatewayError"></a>

## GatewayError

<a id="skaldic.traust.session.SessionDeniedError"></a>

## SessionDeniedError

<a id="skaldic.traust.session.SessionExpiredError"></a>

## SessionExpiredError

<a id="skaldic.traust.session.ToolDeniedError"></a>

## ToolDeniedError

<a id="skaldic.traust.session.HttpClient"></a>

## HttpClient

<a id="skaldic.traust.session.TaskManifest"></a>

## TaskManifest

<a id="skaldic.traust.session.User"></a>

## User

<a id="skaldic.traust.session.AgentSession"></a>

## AgentSession

```python
class AgentSession()
```

An active task session with the Traust gateway.

Manages a scoped capability token for the duration of one agent task.
Every tool call made through :meth:`call` is validated against that token
— the agent can only use the tools and resources declared in the manifest
passed to :meth:`open`.

Do not construct directly. Use the :meth:`open` classmethod, which
contacts the gateway, evaluates the manifest against the active policy,
and returns an initialised session::

manifest = TaskManifest(
task_type="summarise_document",
agent_id="agent-summariser-v1",
delegating_user_id="user-123",
requested_tools=["read_document", "call_llm"],
)
user = User(id="user-123", roles=["analyst"])

async with await AgentSession.open(
gateway_url="http://localhost:8000",
api_key="your-api-key",
manifest=manifest,
user=user,
) as session:
result = await session.call("read_document", "read", {"id": "doc_abc"})

The session can be used as an async context manager (recommended) or
managed manually via :meth:`close`.

**Attributes**:

- `session_id` - Read-only identifier assigned by the gateway when the
  session was opened. Appears in all audit log entries for this
  session.

<a id="skaldic.traust.session.AgentSession.__init__"></a>

#### \_\_init\_\_

```python
def __init__(gateway_url: str, api_key: str, session_id: str, token: str,
             http_client: HttpClient) -> None
```

<a id="skaldic.traust.session.AgentSession.session_id"></a>

#### session\_id

```python
@property
def session_id() -> str
```

Gateway-assigned session identifier.

Included in every audit log entry for this session. Use this when
correlating SDK activity with the Traust audit log or operator
dashboard.

<a id="skaldic.traust.session.AgentSession.open"></a>

#### open

```python
@classmethod
async def open(cls,
               gateway_url: str,
               api_key: str,
               manifest: TaskManifest,
               user: User,
               http_client: HttpClient | None = None) -> "AgentSession"
```

Open a task session with the Traust gateway.

Sends the manifest and user context to the gateway, which evaluates
them against the active policy. On success, a scoped capability token
is issued and an :class:`AgentSession` is returned. On denial, a
:exc:`SessionDeniedError` is raised immediately.

**Arguments**:

- `gateway_url` - Base URL of the Traust gateway
  (e.g. ``"http://localhost:8000"``).
- `api_key` - API key issued by the gateway operator.
- `manifest` - Declares the task intent — type, agent, delegating user,
  requested tools and resources.
- `user` - The human user the agent is acting on behalf of. Agent
  permissions are always bounded by this user's permissions.
- `http_client` - Optional custom HTTP client. Pass a subclass or mock
  to avoid real network calls in tests.
  

**Returns**:

  An :class:`AgentSession` ready to make tool calls.
  

**Raises**:

- `SessionDeniedError` - The policy engine denied the session.
- `GatewayError` - Unexpected HTTP error from the gateway (e.g. invalid
  API key, gateway unavailable).

<a id="skaldic.traust.session.AgentSession.call"></a>

#### call

```python
async def call(tool: str, operation: str, params: dict[str,
                                                       Any]) -> dict[str, Any]
```

Make a tool call through the Traust gateway.

The gateway validates the capability token, runs the configured
guardrail pipeline (schema, rate, scope, injection checks pre-execution;
content and drift checks post-execution), executes the tool, and
returns the result. The entire interaction is recorded in the audit log.

**Arguments**:

- `tool` - Name of the tool to invoke. Must be listed in the session
  manifest's ``requested_tools`` — calls to unlisted tools are
  denied immediately.
- `operation` - The operation to perform on the tool
  (e.g. ``"read"``, ``"write"``, ``"complete"``). The available
  operations depend on the tool's registration in the gateway.
- `params` - Tool-specific parameters passed to the tool. These are
  validated by the guardrail pipeline and may be rewritten by
  the gateway (e.g. to inject data-scope filters) before
  reaching the tool.
  

**Returns**:

  The tool's result as a plain dict. The structure depends on the
  tool — consult the tool's documentation or the gateway's tool
  registry.
  

**Raises**:

- `ToolDeniedError` - The tool call was denied by policy or a guardrail.
  The session remains active; other tool calls can still be made.
- `EscalationPendingError` - A guardrail flagged the call and suspended
  the session pending operator review. No further tool calls can
  be made until the escalation is resolved.
- `SessionExpiredError` - The capability token has expired or been
  revoked. Open a new session via :meth:`open` to continue.
- `GatewayError` - Unexpected HTTP error from the gateway.

<a id="skaldic.traust.session.AgentSession.close"></a>

#### close

```python
async def close() -> None
```

Close the session.

Sessions expire naturally when their TTL elapses. Calling ``close``
is a clean-up signal and is safe to call multiple times. When using
the session as an async context manager, ``close`` is called
automatically on exit.

<a id="skaldic.traust.models"></a>

# skaldic.traust.models

Request models for Skaldic Traust.

These models are passed to :meth:`AgentSession.open` and describe the agent's
declared intent for a task session. The gateway evaluates them against the
active policy before issuing a capability token.

<a id="skaldic.traust.models.annotations"></a>

## annotations

<a id="skaldic.traust.models.Any"></a>

## Any

<a id="skaldic.traust.models.BaseModel"></a>

## BaseModel

<a id="skaldic.traust.models.Field"></a>

## Field

<a id="skaldic.traust.models.TaskManifest"></a>

## TaskManifest

```python
class TaskManifest(BaseModel)
```

Declares the intent of an agent task session.

The gateway evaluates this manifest against the active policy to decide
whether to issue a capability token. Permissions granted are always a
strict subset of the delegating user's permissions, further narrowed by
the task type.

All fields are included in the audit log for every session.

**Example**:

  ::
  
  manifest = TaskManifest(
  task_type="summarise_document",
  agent_id="agent-summariser-v1",
  delegating_user_id="user-123",
  requested_tools=["read_document", "call_llm"],
- `requested_resources=[{"type"` - "document", "id": "doc_abc"}],
  ttl_requested_seconds=300,
  )
  

**Attributes**:

- `task_type` - Logical identifier for the kind of work being performed.
  Must match a task type registered in the gateway's policy store
  (e.g. ``"summarise_document"``, ``"web_research"``).
- `agent_id` - Registered identifier of the agent opening the session.
  Used for rate limiting, audit logging, and trust-tier lookup.
- `delegating_user_id` - Identity of the human user on whose behalf the
  agent is acting. Agent permissions are always bounded by this
  user's permissions — the agent can never exceed them.
- `requested_tools` - Names of the tools the agent expects to call during
  this session (e.g. ``["read_document", "call_llm"]``). Calls to
  tools not listed here will be denied by the gateway.
- `requested_resources` - Resources the agent expects to access, expressed
  as a list of dicts with at least a ``"type"`` and ``"id"`` key
  (e.g. ``[{"type": "document", "id": "doc_abc"}]``). Used by
  the policy engine to scope data access.
- `ttl_requested_seconds` - Requested lifetime of the capability token in
  seconds. The gateway may issue a shorter TTL based on policy.
  Defaults to ``300`` (5 minutes).

<a id="skaldic.traust.models.TaskManifest.task_type"></a>

#### task\_type

<a id="skaldic.traust.models.TaskManifest.agent_id"></a>

#### agent\_id

<a id="skaldic.traust.models.TaskManifest.delegating_user_id"></a>

#### delegating\_user\_id

<a id="skaldic.traust.models.TaskManifest.requested_tools"></a>

#### requested\_tools

<a id="skaldic.traust.models.TaskManifest.requested_resources"></a>

#### requested\_resources

<a id="skaldic.traust.models.TaskManifest.ttl_requested_seconds"></a>

#### ttl\_requested\_seconds

<a id="skaldic.traust.models.User"></a>

## User

```python
class User(BaseModel)
```

Represents the human user delegating authority to the agent.

The gateway uses this to look up the user's permissions in the policy
store and ensure the agent never acts beyond what the user is allowed
to do themselves.

**Example**:

  ::
  
  user = User(id="user-123", roles=["analyst"], data_scope="own")
  

**Attributes**:

- `id` - Unique identifier for the user in the operator's system.
- `roles` - Roles assigned to the user (e.g. ``["analyst"]``,
  ``["admin"]``). The policy engine uses these to determine
  what the user — and therefore the agent — is permitted to do.
- `data_scope` - Controls which data the user (and agent) can access.
  Common values:
  
  - ``"own"`` — only data belonging to this user (default)
  - ``"team"`` — data visible to the user's team
  - ``"all"`` — unrestricted data access (typically admin-only)

<a id="skaldic.traust.models.User.id"></a>

#### id

<a id="skaldic.traust.models.User.roles"></a>

#### roles

<a id="skaldic.traust.models.User.data_scope"></a>

#### data\_scope

<a id="skaldic.traust.exceptions"></a>

# skaldic.traust.exceptions

Exception hierarchy for Skaldic Traust.

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

<a id="skaldic.traust.exceptions.TraustError"></a>

## TraustError

```python
class TraustError(Exception)
```

Base class for all Skaldic Traust SDK errors.

Catch this to handle any SDK error without caring about the specific type.

<a id="skaldic.traust.exceptions.SessionDeniedError"></a>

## SessionDeniedError

```python
class SessionDeniedError(TraustError)
```

Raised by :meth:`AgentSession.open` when the policy engine denies the session.

This means the declared :class:`TaskManifest` was evaluated and rejected
before any capability token was issued. The agent cannot proceed with this
task — the denial reason and policy version are available for logging.

**Attributes**:

- `reason` - Machine-readable denial reason returned by the policy engine
  (e.g. ``"task-type-not-permitted"``, ``"agent-not-registered"``).
- `policy_version` - Version identifier (git commit hash) of the policy
  that produced this decision. Useful for auditing and debugging.

<a id="skaldic.traust.exceptions.SessionDeniedError.__init__"></a>

#### \_\_init\_\_

```python
def __init__(reason: str, policy_version: str) -> None
```

<a id="skaldic.traust.exceptions.ToolDeniedError"></a>

## ToolDeniedError

```python
class ToolDeniedError(TraustError)
```

Raised by :meth:`AgentSession.call` when a tool call is denied.

The session itself remains active — only this specific tool call was
blocked. The agent can inspect the denial reason, inform the user or
orchestrator, and continue with other tool calls if appropriate.

**Attributes**:

- `reason` - Machine-readable denial reason (e.g.
- ```"tool_not_permitted` - database"``,
  ``"resource_out_of_scope"``).
- `audit_id` - Identifier of the audit event recorded for this denial.
  Use this when correlating SDK exceptions with the gateway's
  audit log.

<a id="skaldic.traust.exceptions.ToolDeniedError.__init__"></a>

#### \_\_init\_\_

```python
def __init__(reason: str, audit_id: str) -> None
```

<a id="skaldic.traust.exceptions.EscalationPendingError"></a>

## EscalationPendingError

```python
class EscalationPendingError(TraustError)
```

Raised by :meth:`AgentSession.call` when a guardrail escalation occurs.

A guardrail (e.g. scope drift, injection detection) flagged this call and
suspended the session pending operator review. The agent **cannot make
further tool calls** until an operator approves or rejects the escalation
via the Traust dashboard.

On receiving this exception the agent should stop, surface the situation
to the user or orchestrator, and wait for the escalation to be resolved
out of band.

**Attributes**:

- `escalation_id` - Unique identifier for the escalation record in the
  operator's review queue. Can be used to poll or reference the
  escalation externally.
- `audit_id` - Identifier of the audit event that triggered the escalation.

<a id="skaldic.traust.exceptions.EscalationPendingError.__init__"></a>

#### \_\_init\_\_

```python
def __init__(escalation_id: str, audit_id: str) -> None
```

<a id="skaldic.traust.exceptions.SessionExpiredError"></a>

## SessionExpiredError

```python
class SessionExpiredError(TraustError)
```

Raised by :meth:`AgentSession.call` when the capability token is no longer valid.

This happens when the token's TTL has elapsed or an operator has explicitly
revoked the session. Call :meth:`AgentSession.open` to open a new session
and obtain a fresh token before continuing.

<a id="skaldic.traust.exceptions.GatewayError"></a>

## GatewayError

```python
class GatewayError(TraustError)
```

Raised when the gateway returns an unexpected HTTP error (4xx/5xx).

This indicates a problem at the infrastructure level rather than a policy
decision — for example, an invalid API key (``401``), a rate limit
(``429``), or a transient gateway unavailability (``503``).

**Attributes**:

- `status_code` - The HTTP status code returned by the gateway.
- `detail` - Human-readable detail message extracted from the response body.

<a id="skaldic.traust.exceptions.GatewayError.__init__"></a>

#### \_\_init\_\_

```python
def __init__(status_code: int, detail: str) -> None
```

<a id="skaldic.traust.http_client"></a>

# skaldic.traust.http\_client

Thin async HTTP client wrapper used by AgentSession.

Injectable for testing — pass a subclass or mock to :meth:`AgentSession.open`
to avoid real network calls::

    class FakeHttpClient(HttpClient):
        async def post(self, url, headers, json):
            return fake_response(200, {...})

<a id="skaldic.traust.http_client.Any"></a>

## Any

<a id="skaldic.traust.http_client.httpx"></a>

## httpx

<a id="skaldic.traust.http_client.HttpClient"></a>

## HttpClient

```python
class HttpClient()
```

Wraps ``httpx.AsyncClient`` for gateway communication.

Creates a new ``httpx.AsyncClient`` per request (stateless). Subclass or
replace entirely in tests to avoid real network calls.

**Arguments**:

- `timeout` - Request timeout in seconds. Applies to both the connection
  and the read phase. Defaults to ``30.0``.

<a id="skaldic.traust.http_client.HttpClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(timeout: float = 30.0) -> None
```

<a id="skaldic.traust.http_client.HttpClient.post"></a>

#### post

```python
async def post(url: str, headers: dict[str, str], json: Any) -> httpx.Response
```

Send an HTTP POST request and return the response.

**Arguments**:

- `url` - Full URL to POST to.
- `headers` - HTTP headers to include in the request.
- `json` - Request body, serialised as JSON.
  

**Returns**:

  The :class:`httpx.Response`. The caller is responsible for
  checking the status code.

