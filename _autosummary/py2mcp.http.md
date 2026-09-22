# py2mcp.http

Serve a py2mcp `FastMCP` server over Streamable HTTP with optional OAuth 2.1.

The *remote* counterpart to [`py2mcp.serve`](py2mcp.serve.md#module-py2mcp.serve) (stdio). A *remote* MCP server (e.g. a claude.ai custom connector) is reached over public
HTTPS from the vendor’s cloud and authenticates with **OAuth 2.1**. Per the MCP
authorization spec the MCP server is an OAuth 2.1 **resource server** — it
*validates* bearer tokens minted by a **managed identity provider** (the
authorization server) and **never issues tokens itself**. Two hard rules fall out
of that and are enforced here by construction:

- **Audience binding (RFC 8707).** The verifier checks the token’s `aud` equals
  *this* server’s resource id, so a token minted for another service cannot be
  replayed here (the confused-deputy defense).
- **No token passthrough.** This layer only *verifies* the inbound token; it never
  forwards it upstream. Any upstream call your tools make must use their own
  credentials.

It wraps FastMCP’s native machinery (no transport/OAuth code is reinvented):

- [`mk_auth_provider()`](#py2mcp.http.mk_auth_provider) — an auth-config dict → a
  `fastmcp.server.auth.RemoteAuthProvider` (a `JWTVerifier` resource server
  that validates the IdP’s JWTs and publishes the RFC 9728
  `/.well-known/oauth-protected-resource` document pointing at the IdP).
- [`mk_http_app()`](#py2mcp.http.mk_http_app) — build the server (via [`py2mcp.mk_mcp_from_refs()`](py2mcp.md#py2mcp.mk_mcp_from_refs)),
  attach the auth provider, and return a Streamable-HTTP **ASGI app** to run under
  any ASGI server (uvicorn, gunicorn, a serverless adapter).
- [`serve_http()`](#py2mcp.http.serve_http) — build and *run* it (blocking), for a self-hosted process.

`coact`’s `claude-remote-connector` publish target scaffolds a deployable
service around these — coact writes packaging, py2mcp builds and serves the MCP
server (the same division of labour as the stdio `.mcpb` path).

Building the app performs no network I/O, so it is safe to do at import time:

```pycon
>>> from py2mcp.http import mk_http_app
>>> app = mk_http_app(['os.path:basename'], name='Paths')
>>> [route.path for route in app.routes]
['/mcp']
```

### Module Attributes

| [`SUPPORTED_AUTH_TYPES`](#py2mcp.http.SUPPORTED_AUTH_TYPES)   | Auth `type` values [`mk_auth_provider()`](#py2mcp.http.mk_auth_provider) understands.   |
|-------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|
| [`DFLT_TRANSPORT`](#py2mcp.http.DFLT_TRANSPORT)         | Default Streamable-HTTP transport (the current remote MCP transport).                                 |

### Functions

| [`mk_auth_provider`](#py2mcp.http.mk_auth_provider)(auth)                        | Build a FastMCP **resource-server** auth provider from an auth-config dict.    |
|------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`mk_http_app`](#py2mcp.http.mk_http_app)(refs, \*[, name, auth, ...])      | Build a Streamable-HTTP **ASGI app** from `refs` (+ optional OAuth).           |
| [`serve_http`](#py2mcp.http.serve_http)(refs, \*[, name, host, port, ...]) | Build and **run** a Streamable-HTTP MCP server (blocking) via FastMCP/uvicorn. |

### py2mcp.http.DFLT_TRANSPORT *= 'streamable-http'*

Default Streamable-HTTP transport (the current remote MCP transport).

### py2mcp.http.SUPPORTED_AUTH_TYPES *= ('jwt',)*

Auth `type` values [`mk_auth_provider()`](#py2mcp.http.mk_auth_provider) understands. `'jwt'` is the
vendor-neutral resource-server pattern (validate a managed IdP’s JWTs);
managed-provider shortcuts (auth0/workos/…) can be added as new types.

### py2mcp.http.mk_auth_provider(auth)

Build a FastMCP **resource-server** auth provider from an auth-config dict.

`auth` is `None`/falsy (no auth) or a dict with a `type` key:

`type='jwt'` (default) — validate JWTs issued by a managed IdP. Keys:

- `jwks_uri` *or* `public_key` — where to get the IdP’s signing key(s).
- `issuer` — the IdP issuer URL (the token’s `iss`).
- `audience` (**required**) — **this** server’s resource id (the token’s
  `aud`). RFC 8707 audience binding is mandatory: it stops a token minted for
  another service being replayed here (the confused-deputy defense), so this
  helper refuses to build a verifier that would skip it.
- `authorization_servers` (or a single `issuer`) — IdP issuer URL(s)
  advertised in the RFC 9728 protected-resource metadata.
- `base_url` — this server’s public base URL.
- `required_scopes` (optional) — scopes every request must carry.

Building the provider performs **no network I/O** (key fetching is lazy, on the
first request), so this is safe to call at scaffold/import time.

* **Parameters:**
  **auth** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]) – The auth-config dict described above, or `None`/`{}` for no
  authentication.
* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]
* **Returns:**
  A `RemoteAuthProvider` (a resource server), or `None` when `auth`
  is falsy.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – `auth` is not a dict, its `type` is not supported, or a
      required key (`jwks_uri`/`public_key`, `base_url`,
      `audience`, `authorization_servers`/`issuer`) is missing.

### Examples

```pycon
>>> mk_auth_provider(None) is None
True
>>> provider = mk_auth_provider({
...     'type': 'jwt',
...     'jwks_uri': 'https://idp.example.com/.well-known/jwks.json',
...     'issuer': 'https://idp.example.com',
...     'audience': 'https://conn.example.com/mcp',
...     'base_url': 'https://conn.example.com',
... })
>>> type(provider).__name__
'RemoteAuthProvider'
>>> provider.authorization_servers
['https://idp.example.com']
```

Leaving out the audience is refused rather than silently unchecked:

```pycon
>>> mk_auth_provider({'type': 'jwt', 'jwks_uri': 'https://idp.example.com/jwks',
...                   'base_url': 'https://conn.example.com'})
Traceback (most recent call last):
    ...
ValueError: jwt auth needs 'audience' (this server's resource id). ...
```

#### SEE ALSO
[`mk_http_app()`](#py2mcp.http.mk_http_app): where the provider is attached to a server.

### py2mcp.http.mk_http_app(refs, , name='py2mcp Server', auth=None, input_trans=None, transport='streamable-http', path=None, stateless_http=None, middleware=None, instructions=None)

Build a Streamable-HTTP **ASGI app** from `refs` (+ optional OAuth).

Returns the ASGI application (a Starlette app), so any ASGI server can run it:

```default
# server/app.py
from py2mcp.http import mk_http_app
app = mk_http_app(['mypkg.tools:summarize'], name='My Connector', auth=AUTH)
# then:  uvicorn server.app:app --host 0.0.0.0 --port 8000
```

Builds the app with **no network I/O**.

* **Parameters:**
  * **refs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – `'module:function'` references, one per tool.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Server name.
  * **auth** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]) – Resolved by [`mk_auth_provider()`](#py2mcp.http.mk_auth_provider) (`None` → no auth; a remote
    connector should always set it).
  * **input_trans** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Forwarded to [`py2mcp.mk_mcp_from_refs()`](py2mcp.md#py2mcp.mk_mcp_from_refs).
  * **transport** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The FastMCP HTTP transport; `DFLT_TRANSPORT` is
    Streamable HTTP.
  * **path** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – URL path the MCP endpoint is mounted at; `None` keeps
    FastMCP’s default (`/mcp`).
  * **stateless_http** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`bool`](https://docs.python.org/3/builtins/functions.html#bool)]) – `True` is recommended behind a load balancer (MCP
    sessions are stateful, so default in-memory sessions break across
    replicas — go stateless or externalize session state). `None`
    keeps FastMCP’s default.
  * **middleware** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – A single FastMCP middleware or a list, attached for
    cross-cutting concerns — metering, logging, rate limiting. Because
    `auth` runs first, it can read the authenticated caller via
    `fastmcp.server.dependencies.get_access_token()`.
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – The server’s model-facing description (surfaced to the
    connecting client/model).
* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)
* **Returns:**
  The Starlette ASGI application.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – `auth` is malformed (see [`mk_auth_provider()`](#py2mcp.http.mk_auth_provider)) or a
      reference cannot be parsed (see [`py2mcp.mk_mcp_from_refs()`](py2mcp.md#py2mcp.mk_mcp_from_refs)).

### Examples

```pycon
>>> app = mk_http_app(['os.path:basename'], name='Paths')
>>> callable(app)
True
>>> [route.path for route in app.routes]
['/mcp']
```

With OAuth and a custom mount path, the RFC 9728 protected-resource
metadata route is added next to the endpoint:

```pycon
>>> AUTH = {
...     'type': 'jwt',
...     'jwks_uri': 'https://idp.example.com/.well-known/jwks.json',
...     'issuer': 'https://idp.example.com',
...     'audience': 'https://conn.example.com/mcp',
...     'base_url': 'https://conn.example.com',
... }
>>> app = mk_http_app(['os.path:basename'], name='Paths', auth=AUTH, path='/api/mcp')
>>> [route.path for route in app.routes]
['/.well-known/oauth-protected-resource/api/mcp', '/api/mcp']
```

#### SEE ALSO
[`serve_http()`](#py2mcp.http.serve_http): build and run in-process instead of returning the app.
[`py2mcp.serve.serve_stdio()`](py2mcp.serve.md#py2mcp.serve.serve_stdio): the local stdio counterpart.

### py2mcp.http.serve_http(refs, , name='py2mcp Server', host='127.0.0.1', port=8000, auth=None, input_trans=None, transport='streamable-http', stateless_http=None, middleware=None, instructions=None)

Build and **run** a Streamable-HTTP MCP server (blocking) via FastMCP/uvicorn.

For a self-hosted process. Binds `127.0.0.1` by default — expose a public
interface only behind a TLS-terminating reverse proxy (a remote connector must
be reachable over public **HTTPS**, and binding locally is the spec’s
DNS-rebinding-safe default). `auth` is resolved by [`mk_auth_provider()`](#py2mcp.http.mk_auth_provider);
`middleware` (a single FastMCP middleware or a list) is attached as in
[`mk_http_app()`](#py2mcp.http.mk_http_app); `instructions` sets the server’s model-facing description.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
