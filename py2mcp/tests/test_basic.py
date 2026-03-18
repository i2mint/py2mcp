"""Tests for py2mcp functionality."""

import pytest
import asyncio

from py2mcp import mk_mcp_server, mk_mcp_from_store, mk_input_trans


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


def _call(mcp, tool_name, args=None):
    """Call a tool on an MCP server and return the structured result."""
    result = _run(mcp.call_tool(tool_name, args or {}))
    return result.structured_content.get('result', result.structured_content)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_single_function():
    """Test creating an MCP server from a single function."""
    def add(a: int, b: int) -> int:
        return a + b

    mcp = mk_mcp_server(add)
    assert mcp is not None
    assert mcp.name == "py2mcp Server"


def test_multiple_functions():
    """Test creating an MCP server from multiple functions."""
    def add(a: int, b: int) -> int:
        return a + b

    def multiply(a: int, b: int) -> int:
        return a * b

    mcp = mk_mcp_server([add, multiply], name="Math Server")
    assert mcp.name == "Math Server"


def test_input_transformation():
    """Test input transformation."""
    trans = mk_input_trans({'x': int, 'y': float})

    result = trans({'x': '42', 'y': '3.14', 'z': 'unchanged'})
    assert result['x'] == 42
    assert result['y'] == 3.14
    assert result['z'] == 'unchanged'


def test_input_trans_with_none():
    """Test that None input_trans works correctly."""
    trans = mk_input_trans(None)

    result = trans({'a': 1, 'b': 2})
    assert result == {'a': 1, 'b': 2}


def test_store_to_mcp():
    """Test creating MCP server from a store."""
    store = {'item1': 'value1', 'item2': 'value2'}

    mcp = mk_mcp_from_store(store, name='item')
    assert mcp.name == 'item Store'


def test_store_operations():
    """Test that store operations work correctly."""
    from py2mcp.util import store_to_funcs

    store = {'a': 1, 'b': 2}
    funcs = store_to_funcs(store, name='item')

    assert len(funcs) == 4

    func_names = [f.__name__ for f in funcs]
    assert 'list_items' in func_names
    assert 'get_item' in func_names
    assert 'set_item' in func_names
    assert 'delete_item' in func_names


def test_store_list_operation():
    """Test list operation on store."""
    from py2mcp.util import store_to_funcs

    store = {'a': 1, 'b': 2, 'c': 3}
    funcs = {f.__name__: f for f in store_to_funcs(store, name='item')}

    items = funcs['list_items']()
    assert set(items) == {'a', 'b', 'c'}


def test_store_get_operation():
    """Test get operation on store."""
    from py2mcp.util import store_to_funcs

    store = {'x': 100, 'y': 200}
    funcs = {f.__name__: f for f in store_to_funcs(store, name='item')}

    assert funcs['get_item']('x') == 100
    assert funcs['get_item']('y') == 200


def test_store_set_operation():
    """Test set operation on store."""
    from py2mcp.util import store_to_funcs

    store = {}
    funcs = {f.__name__: f for f in store_to_funcs(store, name='item')}

    funcs['set_item']('new_key', 'new_value')
    assert store['new_key'] == 'new_value'


def test_store_delete_operation():
    """Test delete operation on store."""
    from py2mcp.util import store_to_funcs

    store = {'to_delete': 'value'}
    funcs = {f.__name__: f for f in store_to_funcs(store, name='item')}

    funcs['delete_item']('to_delete')
    assert 'to_delete' not in store


def test_store_custom_plural():
    """Test store functions with custom plural form."""
    from py2mcp.util import store_to_funcs

    store = {'a': 1}
    funcs = store_to_funcs(store, name='cactus', plural='cacti')
    func_names = [f.__name__ for f in funcs]
    assert func_names == ['list_cacti', 'get_cactus', 'set_cactus', 'delete_cactus']


def test_invalid_input():
    """Test that invalid inputs raise appropriate errors."""
    with pytest.raises(TypeError):
        mk_mcp_server("not a function")

    with pytest.raises(TypeError):
        mk_mcp_server([lambda x: x, "not a function"])


# ---------------------------------------------------------------------------
# End-to-end tests (calling tools through the MCP server)
# ---------------------------------------------------------------------------


def test_e2e_call_tool():
    """End-to-end: call a tool through the MCP server."""
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    mcp = mk_mcp_server(add)
    assert _call(mcp, 'add', {'a': 3, 'b': 4}) == 7


def test_e2e_multiple_tools():
    """End-to-end: register and call multiple tools."""
    def add(a: int, b: int) -> int:
        """Add."""
        return a + b

    def multiply(a: int, b: int) -> int:
        """Multiply."""
        return a * b

    mcp = mk_mcp_server([add, multiply])

    assert _call(mcp, 'add', {'a': 2, 'b': 3}) == 5
    assert _call(mcp, 'multiply', {'a': 2, 'b': 3}) == 6


def test_e2e_list_tools():
    """End-to-end: list registered tools."""
    def greet(name: str) -> str:
        """Greet someone."""
        return f"Hello, {name}!"

    def farewell(name: str) -> str:
        """Say goodbye."""
        return f"Goodbye, {name}!"

    mcp = mk_mcp_server([greet, farewell])
    tools = _run(mcp.list_tools())
    tool_names = {t.name for t in tools}
    assert tool_names == {'greet', 'farewell'}


def test_e2e_store_crud():
    """End-to-end: full CRUD cycle through the MCP server."""
    store = {'a': 1, 'b': 2}
    mcp = mk_mcp_from_store(store, name='item')

    # List
    keys = _call(mcp, 'list_items')
    assert set(keys) == {'a', 'b'}

    # Get
    assert _call(mcp, 'get_item', {'key': 'a'}) == 1

    # Set
    _call(mcp, 'set_item', {'key': 'c', 'value': 3})
    assert store['c'] == 3

    # Delete
    _call(mcp, 'delete_item', {'key': 'a'})
    assert 'a' not in store

    # List after mutations
    keys = _call(mcp, 'list_items')
    assert set(keys) == {'b', 'c'}


def test_e2e_input_trans():
    """End-to-end: input transformation through the MCP server."""
    def compute(x: int, y: int) -> int:
        """Compute x + y after transformation."""
        return x + y

    trans = mk_input_trans({'x': lambda v: v * 10})
    mcp = mk_mcp_server(compute, input_trans=trans)

    assert _call(mcp, 'compute', {'x': 3, 'y': 1}) == 31


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
