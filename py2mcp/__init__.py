"""py2mcp: Quick MCP server creation from Python functions.

This package provides a simple, Pythonic way to create Model Context Protocol (MCP)
servers from ordinary Python functions. Built on FastMCP, it handles all the protocol
complexity while letting you focus on your business logic.

Basic usage:
    >>> from py2mcp import mk_mcp_server
    >>>
    >>> def add(a: int, b: int) -> int:
    ...     '''Add two numbers'''
    ...     return a + b
    >>>
    >>> mcp = mk_mcp_server([add])
    >>> # mcp.run()  # Start the server
"""

from py2mcp.main import mk_mcp_server, mk_mcp_from_store, mk_mcp_from_refs
from py2mcp.trans import mk_input_trans
from py2mcp.util import import_object

__version__ = "0.1.0"

__all__ = [
    "mk_mcp_server",
    "mk_mcp_from_store",
    "mk_mcp_from_refs",
    "mk_input_trans",
    "import_object",
]
