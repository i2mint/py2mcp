"""py2mcp: Quick MCP server creation from Python functions.

Pass ordinary Python functions and get back a Model Context Protocol (MCP)
server, built on FastMCP, with each function registered as a tool. The
``mk_mcp_*`` builders return a server *object* and leave running it to you:
``mcp.run()`` for stdio, or :mod:`py2mcp.serve` and :mod:`py2mcp.http` for a
packaged stdio launcher and a Streamable-HTTP (optionally OAuth 2.1) server.

Main entry points:

- ``mk_mcp_server``: functions in, ``FastMCP`` server out
- ``mk_mcp_from_refs``: the same from ``'module:function'`` strings
- ``mk_mcp_from_store``: list/get/set/delete tools over any ``MutableMapping``
- ``mk_input_trans``: per-argument conversion of tool inputs
- ``serve_stdio`` and ``serve_http``: build from refs and run

>>> from py2mcp import mk_mcp_server
>>> def add(a: int, b: int) -> int:
...     '''Add two numbers'''
...     return a + b
>>> mcp = mk_mcp_server([add])
>>> mcp.name
'py2mcp Server'
>>> # mcp.run()  # Start the server over stdio
"""

from py2mcp.main import mk_mcp_server, mk_mcp_from_store, mk_mcp_from_refs
from py2mcp.serve import serve_stdio, resolve_server_config, load_server_config
from py2mcp.http import mk_http_app, serve_http, mk_auth_provider
from py2mcp.trans import mk_input_trans
from py2mcp.util import import_object, claude_install_link, markdown_install_badge


def _resolve_version() -> str:
    """Read the installed distribution version (SSOT = pyproject), else a sentinel.

    Sourcing ``__version__`` from installed metadata keeps it in step with
    ``pyproject.toml`` (which wads bumps on release) instead of a hand-edited
    literal that silently drifts.
    """
    from importlib.metadata import PackageNotFoundError, version

    try:
        return version("py2mcp")
    except PackageNotFoundError:  # pragma: no cover - only in an uninstalled tree
        return "0.0.0+unknown"


__version__ = _resolve_version()

__all__ = [
    "mk_mcp_server",
    "mk_mcp_from_store",
    "mk_mcp_from_refs",
    "mk_input_trans",
    "import_object",
    # "Add to Claude" connector links (pure strings, no server needed)
    "claude_install_link",
    "markdown_install_badge",
    "serve_stdio",
    "resolve_server_config",
    "load_server_config",
    # remote (Streamable-HTTP + OAuth resource-server) serving
    "mk_http_app",
    "serve_http",
    "mk_auth_provider",
]
