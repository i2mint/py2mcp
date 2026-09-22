# py2mcp

py2mcp: Quick MCP server creation from Python functions.

Pass ordinary Python functions and get back a Model Context Protocol (MCP)
server, built on FastMCP, with each function registered as a tool. The
`mk_mcp_*` builders return a server *object* and leave running it to you:
`mcp.run()` for stdio, or [`py2mcp.serve`](py2mcp.serve.md#module-py2mcp.serve) and [`py2mcp.http`](py2mcp.http.md#module-py2mcp.http) for a
packaged stdio launcher and a Streamable-HTTP (optionally OAuth 2.1) server.

Main entry points:

- `mk_mcp_server`: functions in, `FastMCP` server out
- `mk_mcp_from_refs`: the same from `'module:function'` strings
- `mk_mcp_from_store`: list/get/set/delete tools over any `MutableMapping`
- `mk_input_trans`: per-argument conversion of tool inputs
- `serve_stdio` and `serve_http`: build from refs and run

```pycon
>>> from py2mcp import mk_mcp_server
>>> def add(a: int, b: int) -> int:
...     '''Add two numbers'''
...     return a + b
>>> mcp = mk_mcp_server([add])
>>> mcp.name
'py2mcp Server'
>>> # mcp.run()  # Start the server over stdio
```

### Functions

| [`mk_mcp_server`](#py2mcp.mk_mcp_server)(funcs, \*[, name, input_trans, ...])   | Create an MCP server from Python functions.                                    |
|-------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| [`mk_mcp_from_store`](#py2mcp.mk_mcp_from_store)(store, \*[, name, plural, ...])    | Create an MCP server from a MutableMapping with CRUD operations.               |
| [`mk_mcp_from_refs`](#py2mcp.mk_mcp_from_refs)(refs, \*[, name, ...])              | Create an MCP server from `'module:function'` reference strings.               |
| [`mk_input_trans`](#py2mcp.mk_input_trans)([name_func_relationships])            | Create an input transformation function from name->func mappings.              |
| [`import_object`](#py2mcp.import_object)(ref)                                   | Resolve a `'module.path:attr'` (preferred) or `'module.path.attr'` reference.  |
| [`claude_install_link`](#py2mcp.claude_install_link)(name, mcp_url, \*[, admin])      | Prefilled "Add custom connector" link for claude.ai.                           |
| [`markdown_install_badge`](#py2mcp.markdown_install_badge)(name, mcp_url, \*[, admin])   | Markdown link that installs an MCP server as a claude.ai connector.            |
| [`serve_stdio`](#py2mcp.serve_stdio)(refs, \*[, name, input_trans, ...])      | Build an MCP server from `'module:function'` refs and run it over stdio.       |
| [`resolve_server_config`](#py2mcp.resolve_server_config)(\*[, config, refs, name])      | Merge a config file and explicit `refs`/`name` into `(refs, name)`.            |
| [`load_server_config`](#py2mcp.load_server_config)(path)                             | Load a server config JSON of the form `{"name": str, "refs": [str, ...]}`.     |
| [`mk_http_app`](#py2mcp.mk_http_app)(refs, \*[, name, auth, ...])             | Build a Streamable-HTTP **ASGI app** from `refs` (+ optional OAuth).           |
| [`serve_http`](#py2mcp.serve_http)(refs, \*[, name, host, port, ...])        | Build and **run** a Streamable-HTTP MCP server (blocking) via FastMCP/uvicorn. |
| [`mk_auth_provider`](#py2mcp.mk_auth_provider)(auth)                               | Build a FastMCP **resource-server** auth provider from an auth-config dict.    |

### py2mcp.claude_install_link(name, mcp_url, , admin=False)

Prefilled “Add custom connector” link for claude.ai.

There is no true one-click install for an unlisted MCP server (listing
requires Anthropic review), but this link opens the add-connector modal with
the name and URL already filled in, so the user only has to confirm — which
beats “go to Settings, find Connectors, paste this long URL”.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Connector name to prefill (what the user will see in their list).
  * **mcp_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Full URL of the MCP endpoint, e.g. `https://host/api/x/mcp`.
  * **admin** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Target the org-wide install page instead of the per-user one.
    Use it when an admin is rolling the connector out to a whole
    workspace; the default (`False`) is the personal install.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  The claude.ai URL, safe to paste into a README or a chat message.

```pycon
>>> claude_install_link('snout', 'https://example.com/api/snout_mcp/mcp')
'https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=snout&connectorUrl=https%3A%2F%2Fexample.com%2Fapi%2Fsnout_mcp%2Fmcp'
```

Names and URLs are percent-encoded, so spaces (and `&`) can’t break the
query string:

```pycon
>>> claude_install_link('my server', 'https://x.io/mcp', admin=True)
'https://claude.ai/admin-settings/connectors?modal=add-custom-connector&connectorName=my%20server&connectorUrl=https%3A%2F%2Fx.io%2Fmcp'
```

Note that the link is a convenience, not an access grant: if the server is an
OAuth resource server with an allowlist, a user who isn’t on it can follow
the link, complete the flow, and still be refused. Custom connectors are also
a paid-plan feature, so the link goes nowhere for a Free-plan user.

### py2mcp.import_object(ref)

Resolve a `'module.path:attr'` (preferred) or `'module.path.attr'` reference.

Useful for building MCP servers from configuration strings (e.g. tool
references declared in a file), so callers don’t reimplement the
`importlib` dance. With a colon, everything before it is the module and
everything after it an attribute path; without one, the last dot splits
module from attribute, so `'pkg.mod.Class.method'` cannot be reached in
the dotted form (use `'pkg.mod:Class.method'`).

* **Parameters:**
  **ref** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The reference string; the `module:attr` form is preferred.
* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)
* **Returns:**
  The object the reference names, after importing its module.
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – The reference has no module part or no attribute part.
  * [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – The module part does not import (`ModuleNotFoundError`
        when the module does not exist; a plain `ImportError` if it
        exists but fails while importing).
  * [**AttributeError**](https://docs.python.org/3/builtins/exceptions.html#AttributeError) – The attribute path does not exist on the module.

### Examples

```pycon
>>> import_object('json:dumps')
<function dumps at ...>
>>> import_object('os.path.join')
<function join at ...>
>>> import_object('no-separator')
Traceback (most recent call last):
    ...
ValueError: Invalid object reference 'no-separator'; expected 'module:attr' or 'module.path.attr'.
```

#### SEE ALSO
[`py2mcp.mk_mcp_from_refs()`](#py2mcp.mk_mcp_from_refs): build a server from such references.

### py2mcp.load_server_config(path)

Load a server config JSON of the form `{"name": str, "refs": [str, ...]}`.

Only the shape is checked here; the refs are resolved later, when the
server is built. An actionable error beats a server that starts with no
tools.

* **Parameters:**
  **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – The JSON file to read.
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  The parsed JSON object, untouched, with at least a `refs` list.
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – The file is not valid JSON, or is not a JSON object carrying
        a `refs` list.
  * [**OSError**](https://docs.python.org/3/builtins/exceptions.html#OSError) – The file cannot be read.

### Examples

```pycon
>>> import json, tempfile
>>> from pathlib import Path
>>> path = Path(tempfile.mkdtemp()) / 'py2mcp_config.json'
>>> _ = path.write_text(json.dumps({'name': 'My Tools', 'refs': ['os.path:basename']}))
>>> load_server_config(path)
{'name': 'My Tools', 'refs': ['os.path:basename']}
>>> _ = path.write_text(json.dumps({'name': 'no refs here'}))
>>> load_server_config(path)
Traceback (most recent call last):
    ...
ValueError: py2mcp server config '...py2mcp_config.json' must be a JSON object with a "refs" list, ...
```

#### SEE ALSO
[`resolve_server_config()`](#py2mcp.resolve_server_config): merge the config with command-line refs.

### py2mcp.markdown_install_badge(name, mcp_url, , admin=False)

Markdown link that installs an MCP server as a claude.ai connector.

The dominant use of [`claude_install_link()`](#py2mcp.claude_install_link) is pasting one into a README,
so this saves writing the same link syntax around it. Arguments are those of
[`claude_install_link()`](#py2mcp.claude_install_link).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> markdown_install_badge('snout', 'https://x.io/mcp')
'[Add snout to Claude](https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=snout&connectorUrl=https%3A%2F%2Fx.io%2Fmcp)'
```

### py2mcp.mk_auth_provider(auth)

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
[`mk_http_app()`](#py2mcp.mk_http_app): where the provider is attached to a server.

### py2mcp.mk_http_app(refs, , name='py2mcp Server', auth=None, input_trans=None, transport='streamable-http', path=None, stateless_http=None, middleware=None, instructions=None)

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
  * **auth** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]) – Resolved by [`mk_auth_provider()`](#py2mcp.mk_auth_provider) (`None` → no auth; a remote
    connector should always set it).
  * **input_trans** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Forwarded to [`py2mcp.mk_mcp_from_refs()`](#py2mcp.mk_mcp_from_refs).
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
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – `auth` is malformed (see [`mk_auth_provider()`](#py2mcp.mk_auth_provider)) or a
      reference cannot be parsed (see [`py2mcp.mk_mcp_from_refs()`](#py2mcp.mk_mcp_from_refs)).

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
[`serve_http()`](#py2mcp.serve_http): build and run in-process instead of returning the app.
[`py2mcp.serve.serve_stdio()`](py2mcp.serve.md#py2mcp.serve.serve_stdio): the local stdio counterpart.

### py2mcp.mk_input_trans(name_func_relationships=None)

Create an input transformation function from name->func mappings.

The returned callable takes a tool call’s keyword arguments as a dict and
returns a new dict in which each named argument has been passed through its
converter; arguments with no converter are copied through unchanged. Pass it
as `input_trans` to [`py2mcp.mk_mcp_server()`](#py2mcp.mk_mcp_server) and friends.

* **Parameters:**
  **name_func_relationships** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)]) – Which converter applies to which argument, as
  `{name: func}`, or reversed as `{func: name}` or
  `{func: [name, ...]}` when one converter serves several arguments.
  `None` gives a transformation that only copies the dict.
* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]
* **Returns:**
  A function from a kwargs dict to a new kwargs dict.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – The same argument name is mapped more than once.

### Examples

```pycon
>>> def to_int(x): return int(x)
>>> trans = mk_input_trans({'x': to_int})
>>> trans({'x': '42', 'y': 'hello'})
{'x': 42, 'y': 'hello'}
```

One converter for several arguments, written the reversed way:

```pycon
>>> trans = mk_input_trans({to_int: ['x', 'y']})
>>> trans({'x': '1', 'y': '2', 'z': '3'})
{'x': 1, 'y': 2, 'z': '3'}
```

No mapping means no conversion:

```pycon
>>> mk_input_trans()({'x': '1'})
{'x': '1'}
```

#### SEE ALSO
[`py2mcp.mk_mcp_server()`](#py2mcp.mk_mcp_server): where the returned callable is applied.

### py2mcp.mk_mcp_from_refs(refs, , name='py2mcp Server', input_trans=None, auth=None, middleware=None, instructions=None)

Create an MCP server from `'module:function'` reference strings.

Resolves each reference to a callable via [`py2mcp.util.import_object()`](py2mcp.util.md#py2mcp.util.import_object)
and delegates to [`mk_mcp_server()`](#py2mcp.mk_mcp_server). One call from config strings to a
runnable server — what tools that read tool references from a file (e.g.
`coact`’s `mcp` backend) need.

* **Parameters:**
  * **refs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – `'module.path:attr'` (or `'module.path.attr'`) strings, one per
    tool. Every module is imported when this is called.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the MCP server.
  * **input_trans** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Forwarded to [`mk_mcp_server()`](#py2mcp.mk_mcp_server).
  * **auth** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Forwarded to [`mk_mcp_server()`](#py2mcp.mk_mcp_server); the remote/HTTP path attaches
    its OAuth provider here.
  * **middleware** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Forwarded to [`mk_mcp_server()`](#py2mcp.mk_mcp_server).
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Forwarded to [`mk_mcp_server()`](#py2mcp.mk_mcp_server) as the server’s
    model-facing description.
* **Return type:**
  `FastMCP`
* **Returns:**
  A FastMCP server with one tool per reference, each named after the
  resolved function.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – A reference has no `module` or `attr` part (see
      [`py2mcp.util.import_object()`](py2mcp.util.md#py2mcp.util.import_object), whose import errors propagate too).

### Examples

```pycon
>>> mcp = mk_mcp_from_refs(['os.path:basename', 'os.path:dirname'], name='Paths')
>>> mcp.name
'Paths'
```

The tools are the resolved functions:

```pycon
>>> import asyncio
>>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
['basename', 'dirname']
>>> asyncio.run(mcp.call_tool('basename', {'p': '/a/b/c.txt'})).content[0].text
'c.txt'
```

#### SEE ALSO
[`py2mcp.serve.serve_stdio()`](py2mcp.serve.md#py2mcp.serve.serve_stdio): build from refs and run over stdio.
[`py2mcp.http.mk_http_app()`](py2mcp.http.md#py2mcp.http.mk_http_app): build from refs as an ASGI app.

### py2mcp.mk_mcp_from_store(store, , name='item', plural='', server_name=None, middleware=None, instructions=None)

Create an MCP server from a MutableMapping with CRUD operations.

Generates four tools over the store, `list_<plural>`, `get_<name>`,
`set_<name>` and `delete_<name>`, so any key-value store (a dict, a
`dol` store, a database wrapper) is one call away from being MCP tools.
The store is used live: a tool call reads or writes the mapping you passed.

* **Parameters:**
  * **store** ([`MutableMapping`](https://docs.python.org/3/library/typing.html#typing.MutableMapping)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – A MutableMapping to expose via MCP.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Singular name for items (e.g., ‘project’, ‘user’); used in the
    tool names.
  * **plural** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Plural form used by the list tool (defaults to name + ‘s’).
  * **server_name** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Name of the MCP server (defaults to “{name} Store”).
  * **middleware** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Optional FastMCP middleware (a single middleware or an
    iterable), forwarded to [`mk_mcp_server()`](#py2mcp.mk_mcp_server) — wraps every generated
    CRUD tool call, e.g. to meter or audit store reads and mutations.
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Optional natural-language server description, forwarded to
    [`mk_mcp_server()`](#py2mcp.mk_mcp_server) as the server’s model-facing `instructions`.
* **Return type:**
  `FastMCP`
* **Returns:**
  A FastMCP server with the four CRUD tools.

### Examples

```pycon
>>> import asyncio
>>> projects = {'p1': {'name': 'Project 1'}, 'p2': {'name': 'Project 2'}}
>>> mcp = mk_mcp_from_store(projects, name='project')
>>> mcp.name
'project Store'
>>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
['delete_project', 'get_project', 'list_projects', 'set_project']
>>> asyncio.run(mcp.call_tool('get_project', {'key': 'p1'})).structured_content
{'result': {'name': 'Project 1'}}
```

An irregular plural and an explicit server name:

```pycon
>>> mcp = mk_mcp_from_store({}, name='entry', plural='entries', server_name='Ledger')
>>> mcp.name
'Ledger'
>>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
['delete_entry', 'get_entry', 'list_entries', 'set_entry']
```

#### SEE ALSO
[`py2mcp.util.store_to_funcs()`](py2mcp.util.md#py2mcp.util.store_to_funcs): the CRUD functions without a server.
[`mk_mcp_server()`](#py2mcp.mk_mcp_server): expose your own functions instead.

### py2mcp.mk_mcp_server(funcs, , name='py2mcp Server', input_trans=None, auth=None, middleware=None, instructions=None)

Create an MCP server from Python functions.

This is the main entry point for py2mcp. Pass one or more functions,
and get back a FastMCP server ready to run. Each function becomes one
tool, named after the function, with its signature and docstring as the
tool’s schema and description.

* **Parameters:**
  * **funcs** (`Union`[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable), [`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]]) – A function or iterable of functions to expose as MCP tools.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the MCP server.
  * **input_trans** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Called with the dict of keyword arguments of every tool
    call; the dict it returns is what the function receives. Build one
    with [`py2mcp.mk_input_trans()`](#py2mcp.mk_input_trans). `None` passes arguments
    through untouched.
  * **auth** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Optional `fastmcp.server.auth` provider attached at construction —
    used by the remote (HTTP) path for OAuth 2.1 (see [`py2mcp.http`](py2mcp.http.md#module-py2mcp.http)).
    `None` (the default) leaves the server unauthenticated, which is
    correct for the local stdio path.
  * **middleware** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Optional FastMCP middleware (a single middleware or a list),
    attached at construction, for cross-cutting concerns that must wrap
    *every* tool call — usage metering, cost logging, audit, rate limiting.
    Preferred over decorating each tool: you can’t forget to wrap one (a
    missed paid tool means untracked cost). On the remote path `auth`
    runs first, so a middleware can read the authenticated caller via
    `fastmcp.server.dependencies.get_access_token()`.
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Optional natural-language description of the server, surfaced
    to the client/model as the server’s `instructions` — a good place to
    explain what the tools do and the intended workflow. `None` (default)
    leaves it unset.
* **Return type:**
  `FastMCP`
* **Returns:**
  A FastMCP server instance ready to run, with one tool per function.

### Examples

```pycon
>>> def add(a: int, b: int) -> int:
...     '''Add two numbers'''
...     return a + b
>>> mcp = mk_mcp_server(add)
>>> mcp.name
'py2mcp Server'
```

Several functions, a server name, and a look at the registered tools:

```pycon
>>> import asyncio
>>> def greet(name: str) -> str:
...     return f"Hello, {name}!"
>>> mcp = mk_mcp_server([add, greet], name="Math & Greetings")
>>> mcp.name
'Math & Greetings'
>>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
['add', 'greet']
```

Calling a tool the way an MCP client would:

```pycon
>>> result = asyncio.run(mcp.call_tool('add', {'a': 2, 'b': 3}))
>>> result.structured_content
{'result': 5}
```

#### SEE ALSO
[`mk_mcp_from_refs()`](#py2mcp.mk_mcp_from_refs): the same from `'module:function'` strings.
[`mk_mcp_from_store()`](#py2mcp.mk_mcp_from_store): CRUD tools generated from a mapping.
[`py2mcp.mk_input_trans()`](#py2mcp.mk_input_trans): build an `input_trans` from per-argument converters.

### py2mcp.resolve_server_config(, config=None, refs=(), name=None)

Merge a config file and explicit `refs`/`name` into `(refs, name)`.

Refs from `--ref` are appended after any from the config file; an explicit
`name` wins over the config’s. Pure (no I/O beyond reading `config`), so
it is unit-testable without standing up a server.

* **Parameters:**
  * **config** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – Path of a JSON config as read by [`load_server_config()`](#py2mcp.load_server_config),
    or `None` for no config file.
  * **refs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Extra `'module:function'` references, appended after the
    config’s.
  * **name** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Server name; overrides the config’s `name`. When neither is
    given, `DFLT_SERVER_NAME`.
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
* **Returns:**
  The merged list of references and the server name.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – Neither the config nor `refs` supplies any reference, or
      the config file is malformed (see [`load_server_config()`](#py2mcp.load_server_config)).

### Examples

```pycon
>>> resolve_server_config(refs=['os.path:basename'], name='Paths')
(['os.path:basename'], 'Paths')
```

With a config file, its refs come first and its name is the fallback:

```pycon
>>> import json, tempfile
>>> from pathlib import Path
>>> path = Path(tempfile.mkdtemp()) / 'py2mcp_config.json'
>>> _ = path.write_text(json.dumps({'name': 'My Tools', 'refs': ['os.path:basename']}))
>>> resolve_server_config(config=path, refs=['os.path:dirname'])
(['os.path:basename', 'os.path:dirname'], 'My Tools')
>>> resolve_server_config(config=path, name='Override')
(['os.path:basename'], 'Override')
```

### py2mcp.serve_http(refs, , name='py2mcp Server', host='127.0.0.1', port=8000, auth=None, input_trans=None, transport='streamable-http', stateless_http=None, middleware=None, instructions=None)

Build and **run** a Streamable-HTTP MCP server (blocking) via FastMCP/uvicorn.

For a self-hosted process. Binds `127.0.0.1` by default — expose a public
interface only behind a TLS-terminating reverse proxy (a remote connector must
be reachable over public **HTTPS**, and binding locally is the spec’s
DNS-rebinding-safe default). `auth` is resolved by [`mk_auth_provider()`](#py2mcp.mk_auth_provider);
`middleware` (a single FastMCP middleware or a list) is attached as in
[`mk_http_app()`](#py2mcp.mk_http_app); `instructions` sets the server’s model-facing description.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### py2mcp.serve_stdio(refs, , name='py2mcp Server', input_trans=None, middleware=None, instructions=None)

Build an MCP server from `'module:function'` refs and run it over stdio.

Blocks, serving the MCP protocol on stdin/stdout until the host disconnects.
Thin wrapper over [`py2mcp.mk_mcp_from_refs()`](#py2mcp.mk_mcp_from_refs) + `FastMCP.run` so that
packaged integrations have one command to launch. No example here: the call
does not return while the server runs.

* **Parameters:**
  * **refs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – `'module:function'` references, one per tool.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Server name.
  * **input_trans** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Forwarded to [`py2mcp.mk_mcp_from_refs()`](#py2mcp.mk_mcp_from_refs).
  * **middleware** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – A single FastMCP middleware or a list, forwarded for
    cross-cutting concerns; logging/metering is as useful on the local
    stdio path as on the remote one.
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – The server’s model-facing description.

#### SEE ALSO
[`py2mcp.http.serve_http()`](py2mcp.http.md#py2mcp.http.serve_http): the same over Streamable HTTP.
[`main()`](py2mcp.main.md#module-py2mcp.main): the command line that calls this.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### Modules

| [`base`](py2mcp.base.md#module-py2mcp.base)   | Private helpers shared by the builders in [`py2mcp.main`](py2mcp.main.md#module-py2mcp.main).   |
|----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| [`http`](py2mcp.http.md#module-py2mcp.http)   | Serve a py2mcp `FastMCP` server over Streamable HTTP with optional OAuth 2.1.                                                |
| [`main`](py2mcp.main.md#module-py2mcp.main)   | Build a `FastMCP` server from Python functions, reference strings, or a store.                                               |
| [`serve`](py2mcp.serve.md#module-py2mcp.serve) | Serve a py2mcp `FastMCP` server over stdio, as a packaged integration launches it.                                           |
| [`trans`](py2mcp.trans.md#module-py2mcp.trans) | Input transformation for py2mcp tools: convert arguments before a function runs.                                             |
| [`util`](py2mcp.util.md#module-py2mcp.util)   | Resolve object references and turn a mapping into CRUD functions.                                                            |
