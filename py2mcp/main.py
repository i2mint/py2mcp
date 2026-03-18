"""Main entry point for creating MCP servers from Python functions."""

from typing import Callable, Iterable, Optional, MutableMapping, Any
from fastmcp import FastMCP

from py2mcp.base import _normalize_to_iterable, _wrap_with_input_trans
from py2mcp.util import store_to_funcs


def mk_mcp_server(
    funcs: Callable | Iterable[Callable],
    *,
    name: str = "py2mcp Server",
    input_trans: Optional[Callable[[dict], dict]] = None,
) -> FastMCP:
    """Create an MCP server from Python functions.
    
    This is the main entry point for py2mcp. Pass one or more functions,
    and get back a FastMCP server ready to run.
    
    Args:
        funcs: A function or iterable of functions to expose as MCP tools
        name: Name of the MCP server
        input_trans: Optional function to transform input kwargs before calling tools
    
    Returns:
        A FastMCP server instance ready to run
    
    Examples:
        >>> def add(a: int, b: int) -> int:
        ...     '''Add two numbers'''
        ...     return a + b
        >>> mcp = mk_mcp_server(add)
        >>> mcp.name
        'py2mcp Server'
        
        >>> def greet(name: str) -> str:
        ...     return f"Hello, {name}!"
        >>> mcp = mk_mcp_server([add, greet], name="Math & Greetings")
        >>> mcp.name
        'Math & Greetings'
    """
    mcp = FastMCP(name)
    
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


def mk_mcp_from_store(
    store: MutableMapping[Any, Any],
    *,
    name: str = "item",
    plural: str = "",
    server_name: Optional[str] = None,
) -> FastMCP:
    """Create an MCP server from a MutableMapping with CRUD operations.

    Automatically generates list, get, set, and delete functions for the store.

    Args:
        store: A MutableMapping to expose via MCP
        name: Singular name for items (e.g., 'project', 'user')
        plural: Plural form (defaults to name + 's')
        server_name: Name of the MCP server (defaults to "{name} Store")

    Returns:
        A FastMCP server with CRUD operations

    Examples:
        >>> projects = {'p1': {'name': 'Project 1'}, 'p2': {'name': 'Project 2'}}
        >>> mcp = mk_mcp_from_store(projects, name='project')
        >>> mcp.name
        'project Store'
    """
    if server_name is None:
        server_name = f"{name} Store"

    funcs = store_to_funcs(store, name=name, plural=plural)

    return mk_mcp_server(funcs, name=server_name)
