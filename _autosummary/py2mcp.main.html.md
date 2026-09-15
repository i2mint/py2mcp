# py2mcp.main

Build a `FastMCP` server from Python functions, reference strings, or a store.

Each builder returns a `FastMCP` server *object* with one tool per function
and does not run it; [`py2mcp.serve`](py2mcp.serve.html.md#module-py2mcp.serve) (stdio) and [`py2mcp.http`](py2mcp.http.html.md#module-py2mcp.http)
(Streamable HTTP) do the running. All three accept `middleware` and
`instructions` and attach them at construction; `mk_mcp_server` and
`mk_mcp_from_refs` take the server `name` directly, while
`mk_mcp_from_store` takes the singular item noun instead and derives the
server name from it (`server_name` overrides).

Main entry points:

- `mk_mcp_server`: register callables as tools
- `mk_mcp_from_refs`: resolve `'module:function'` strings, then the same
- `mk_mcp_from_store`: generate list/get/set/delete tools over a `MutableMapping`

```pycon
>>> from py2mcp.main import mk_mcp_from_refs
>>> mk_mcp_from_refs(['os.path:basename'], name='Paths').name
'Paths'
```

### Functions

| [`mk_mcp_from_refs`](#py2mcp.main.mk_mcp_from_refs)(refs, \*[, name, ...])            | Create an MCP server from `'module:function'` reference strings.   |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [`mk_mcp_from_store`](#py2mcp.main.mk_mcp_from_store)(store, \*[, name, plural, ...])  | Create an MCP server from a MutableMapping with CRUD operations.   |
| [`mk_mcp_server`](#py2mcp.main.mk_mcp_server)(funcs, \*[, name, input_trans, ...]) | Create an MCP server from Python functions.                        |

### py2mcp.main.mk_mcp_from_refs(refs, , name='py2mcp Server', input_trans=None, auth=None, middleware=None, instructions=None)

Create an MCP server from `'module:function'` reference strings.

Resolves each reference to a callable via [`py2mcp.util.import_object()`](py2mcp.util.html.md#py2mcp.util.import_object)
and delegates to [`mk_mcp_server()`](#py2mcp.main.mk_mcp_server). One call from config strings to a
runnable server — what tools that read tool references from a file (e.g.
`coact`’s `mcp` backend) need.

* **Parameters:**
  * **refs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – `'module.path:attr'` (or `'module.path.attr'`) strings, one per
    tool. Every module is imported when this is called.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Name of the MCP server.
  * **input_trans** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Forwarded to [`mk_mcp_server()`](#py2mcp.main.mk_mcp_server).
  * **auth** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Forwarded to [`mk_mcp_server()`](#py2mcp.main.mk_mcp_server); the remote/HTTP path attaches
    its OAuth provider here.
  * **middleware** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Forwarded to [`mk_mcp_server()`](#py2mcp.main.mk_mcp_server).
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Forwarded to [`mk_mcp_server()`](#py2mcp.main.mk_mcp_server) as the server’s
    model-facing description.
* **Return type:**
  `FastMCP`
* **Returns:**
  A FastMCP server with one tool per reference, each named after the
  resolved function.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – A reference has no `module` or `attr` part (see
      [`py2mcp.util.import_object()`](py2mcp.util.html.md#py2mcp.util.import_object), whose import errors propagate too).

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
[`py2mcp.serve.serve_stdio()`](py2mcp.serve.html.md#py2mcp.serve.serve_stdio): build from refs and run over stdio.
[`py2mcp.http.mk_http_app()`](py2mcp.http.html.md#py2mcp.http.mk_http_app): build from refs as an ASGI app.

### py2mcp.main.mk_mcp_from_store(store, , name='item', plural='', server_name=None, middleware=None, instructions=None)

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
    iterable), forwarded to [`mk_mcp_server()`](#py2mcp.main.mk_mcp_server) — wraps every generated
    CRUD tool call, e.g. to meter or audit store reads and mutations.
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Optional natural-language server description, forwarded to
    [`mk_mcp_server()`](#py2mcp.main.mk_mcp_server) as the server’s model-facing `instructions`.
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
[`py2mcp.util.store_to_funcs()`](py2mcp.util.html.md#py2mcp.util.store_to_funcs): the CRUD functions without a server.
[`mk_mcp_server()`](#py2mcp.main.mk_mcp_server): expose your own functions instead.

### py2mcp.main.mk_mcp_server(funcs, , name='py2mcp Server', input_trans=None, auth=None, middleware=None, instructions=None)

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
    with [`py2mcp.mk_input_trans()`](py2mcp.html.md#py2mcp.mk_input_trans). `None` passes arguments
    through untouched.
  * **auth** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – Optional `fastmcp.server.auth` provider attached at construction —
    used by the remote (HTTP) path for OAuth 2.1 (see [`py2mcp.http`](py2mcp.http.html.md#module-py2mcp.http)).
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
[`mk_mcp_from_refs()`](#py2mcp.main.mk_mcp_from_refs): the same from `'module:function'` strings.
[`mk_mcp_from_store()`](#py2mcp.main.mk_mcp_from_store): CRUD tools generated from a mapping.
[`py2mcp.mk_input_trans()`](py2mcp.html.md#py2mcp.mk_input_trans): build an `input_trans` from per-argument converters.
