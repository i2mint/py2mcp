"""Build a ``FastMCP`` server from Python functions, reference strings, or a store.

Each builder returns a ``FastMCP`` server *object* with one tool per function
and does not run it; :mod:`py2mcp.serve` (stdio) and :mod:`py2mcp.http`
(Streamable HTTP) do the running. All three accept ``middleware`` and
``instructions`` and attach them at construction; ``mk_mcp_server`` and
``mk_mcp_from_refs`` take the server ``name`` directly, while
``mk_mcp_from_store`` takes the singular item noun instead and derives the
server name from it (``server_name`` overrides).

Main entry points:

- ``mk_mcp_server``: register callables as tools
- ``mk_mcp_from_refs``: resolve ``'module:function'`` strings, then the same
- ``mk_mcp_from_store``: generate list/get/set/delete tools over a ``MutableMapping``

>>> from py2mcp.main import mk_mcp_from_refs
>>> mk_mcp_from_refs(['os.path:basename'], name='Paths').name
'Paths'
"""

from typing import Callable, Iterable, Optional, MutableMapping, Any
from fastmcp import FastMCP

from py2mcp.base import (
    _normalize_to_iterable,
    _wrap_with_input_trans,
    _normalize_middleware,
)
from py2mcp.util import import_object, store_to_funcs


def mk_mcp_server(
    funcs: Callable | Iterable[Callable],
    *,
    name: str = "py2mcp Server",
    input_trans: Optional[Callable[[dict], dict]] = None,
    auth: Optional[Any] = None,
    middleware: Optional[Any] = None,
    instructions: Optional[str] = None,
) -> FastMCP:
    """Create an MCP server from Python functions.

    This is the main entry point for py2mcp. Pass one or more functions,
    and get back a FastMCP server ready to run. Each function becomes one
    tool, named after the function, with its signature and docstring as the
    tool's schema and description.

    Args:
        funcs: A function or iterable of functions to expose as MCP tools.
        name: Name of the MCP server.
        input_trans: Called with the dict of keyword arguments of every tool
            call; the dict it returns is what the function receives. Build one
            with :func:`py2mcp.mk_input_trans`. ``None`` passes arguments
            through untouched.
        auth: Optional ``fastmcp.server.auth`` provider attached at construction —
            used by the remote (HTTP) path for OAuth 2.1 (see :mod:`py2mcp.http`).
            ``None`` (the default) leaves the server unauthenticated, which is
            correct for the local stdio path.
        middleware: Optional FastMCP middleware (a single middleware or a list),
            attached at construction, for cross-cutting concerns that must wrap
            *every* tool call — usage metering, cost logging, audit, rate limiting.
            Preferred over decorating each tool: you can't forget to wrap one (a
            missed paid tool means untracked cost). On the remote path ``auth``
            runs first, so a middleware can read the authenticated caller via
            ``fastmcp.server.dependencies.get_access_token()``.
        instructions: Optional natural-language description of the server, surfaced
            to the client/model as the server's ``instructions`` — a good place to
            explain what the tools do and the intended workflow. ``None`` (default)
            leaves it unset.

    Returns:
        A FastMCP server instance ready to run, with one tool per function.

    Examples:

        >>> def add(a: int, b: int) -> int:
        ...     '''Add two numbers'''
        ...     return a + b
        >>> mcp = mk_mcp_server(add)
        >>> mcp.name
        'py2mcp Server'

        Several functions, a server name, and a look at the registered tools:

        >>> import asyncio
        >>> def greet(name: str) -> str:
        ...     return f"Hello, {name}!"
        >>> mcp = mk_mcp_server([add, greet], name="Math & Greetings")
        >>> mcp.name
        'Math & Greetings'
        >>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
        ['add', 'greet']

        Calling a tool the way an MCP client would:

        >>> result = asyncio.run(mcp.call_tool('add', {'a': 2, 'b': 3}))
        >>> result.structured_content
        {'result': 5}

    See Also:
        :func:`mk_mcp_from_refs`: the same from ``'module:function'`` strings.
        :func:`mk_mcp_from_store`: CRUD tools generated from a mapping.
        :func:`py2mcp.mk_input_trans`: build an ``input_trans`` from per-argument converters.
    """
    # Pass ``middleware`` only when there is some, so the no-middleware (and
    # empty-list) path stays the old ``FastMCP(name, auth=auth)`` call (no new
    # fastmcp-version floor).
    server_kwargs: dict[str, Any] = {"auth": auth}
    middleware_list = _normalize_middleware(middleware)
    if middleware_list:
        server_kwargs["middleware"] = middleware_list
    if instructions:
        server_kwargs["instructions"] = instructions
    mcp = FastMCP(name, **server_kwargs)

    # Normalize to list of functions
    func_list = list(_normalize_to_iterable(funcs))

    # Register each function as a tool
    for func in func_list:
        # Wrap with input transformation if provided
        if input_trans is not None:
            func = _wrap_with_input_trans(func, input_trans)

        # Register as MCP tool
        mcp.tool(func)

    return mcp


def mk_mcp_from_refs(
    refs: Iterable[str],
    *,
    name: str = "py2mcp Server",
    input_trans: Optional[Callable[[dict], dict]] = None,
    auth: Optional[Any] = None,
    middleware: Optional[Any] = None,
    instructions: Optional[str] = None,
) -> FastMCP:
    """Create an MCP server from ``'module:function'`` reference strings.

    Resolves each reference to a callable via :func:`py2mcp.util.import_object`
    and delegates to :func:`mk_mcp_server`. One call from config strings to a
    runnable server — what tools that read tool references from a file (e.g.
    ``coact``'s ``mcp`` backend) need.

    Args:
        refs: ``'module.path:attr'`` (or ``'module.path.attr'``) strings, one per
            tool. Every module is imported when this is called.
        name: Name of the MCP server.
        input_trans: Forwarded to :func:`mk_mcp_server`.
        auth: Forwarded to :func:`mk_mcp_server`; the remote/HTTP path attaches
            its OAuth provider here.
        middleware: Forwarded to :func:`mk_mcp_server`.
        instructions: Forwarded to :func:`mk_mcp_server` as the server's
            model-facing description.

    Returns:
        A FastMCP server with one tool per reference, each named after the
        resolved function.

    Raises:
        ValueError: A reference has no ``module`` or ``attr`` part (see
            :func:`py2mcp.util.import_object`, whose import errors propagate too).

    Examples:

        >>> mcp = mk_mcp_from_refs(['os.path:basename', 'os.path:dirname'], name='Paths')
        >>> mcp.name
        'Paths'

        The tools are the resolved functions:

        >>> import asyncio
        >>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
        ['basename', 'dirname']
        >>> asyncio.run(mcp.call_tool('basename', {'p': '/a/b/c.txt'})).content[0].text
        'c.txt'

    See Also:
        :func:`py2mcp.serve.serve_stdio`: build from refs and run over stdio.
        :func:`py2mcp.http.mk_http_app`: build from refs as an ASGI app.
    """
    funcs = [import_object(ref) for ref in refs]
    return mk_mcp_server(
        funcs,
        name=name,
        input_trans=input_trans,
        auth=auth,
        middleware=middleware,
        instructions=instructions,
    )


def mk_mcp_from_store(
    store: MutableMapping[Any, Any],
    *,
    name: str = "item",
    plural: str = "",
    server_name: Optional[str] = None,
    middleware: Optional[Any] = None,
    instructions: Optional[str] = None,
) -> FastMCP:
    """Create an MCP server from a MutableMapping with CRUD operations.

    Generates four tools over the store, ``list_<plural>``, ``get_<name>``,
    ``set_<name>`` and ``delete_<name>``, so any key-value store (a dict, a
    ``dol`` store, a database wrapper) is one call away from being MCP tools.
    The store is used live: a tool call reads or writes the mapping you passed.

    Args:
        store: A MutableMapping to expose via MCP.
        name: Singular name for items (e.g., 'project', 'user'); used in the
            tool names.
        plural: Plural form used by the list tool (defaults to name + 's').
        server_name: Name of the MCP server (defaults to "{name} Store").
        middleware: Optional FastMCP middleware (a single middleware or an
            iterable), forwarded to :func:`mk_mcp_server` — wraps every generated
            CRUD tool call, e.g. to meter or audit store reads and mutations.
        instructions: Optional natural-language server description, forwarded to
            :func:`mk_mcp_server` as the server's model-facing ``instructions``.

    Returns:
        A FastMCP server with the four CRUD tools.

    Examples:

        >>> import asyncio
        >>> projects = {'p1': {'name': 'Project 1'}, 'p2': {'name': 'Project 2'}}
        >>> mcp = mk_mcp_from_store(projects, name='project')
        >>> mcp.name
        'project Store'
        >>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
        ['delete_project', 'get_project', 'list_projects', 'set_project']
        >>> asyncio.run(mcp.call_tool('get_project', {'key': 'p1'})).structured_content
        {'result': {'name': 'Project 1'}}

        An irregular plural and an explicit server name:

        >>> mcp = mk_mcp_from_store({}, name='entry', plural='entries', server_name='Ledger')
        >>> mcp.name
        'Ledger'
        >>> sorted(tool.name for tool in asyncio.run(mcp.list_tools()))
        ['delete_entry', 'get_entry', 'list_entries', 'set_entry']

    See Also:
        :func:`py2mcp.util.store_to_funcs`: the CRUD functions without a server.
        :func:`mk_mcp_server`: expose your own functions instead.
    """
    if server_name is None:
        server_name = f"{name} Store"

    funcs = store_to_funcs(store, name=name, plural=plural)

    return mk_mcp_server(
        funcs, name=server_name, middleware=middleware, instructions=instructions
    )
