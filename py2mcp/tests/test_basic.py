"""Basic tests for py2mcp functionality."""

import pytest
from py2mcp import mk_mcp_server, mk_mcp_from_store, mk_input_trans


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
    
    # Should have 4 functions: list, get, set, delete
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
    funcs = dict((f.__name__, f) for f in store_to_funcs(store, name='item'))
    
    items = funcs['list_items']()
    assert set(items) == {'a', 'b', 'c'}


def test_store_get_operation():
    """Test get operation on store."""
    from py2mcp.util import store_to_funcs
    
    store = {'x': 100, 'y': 200}
    funcs = dict((f.__name__, f) for f in store_to_funcs(store, name='item'))
    
    assert funcs['get_item']('x') == 100
    assert funcs['get_item']('y') == 200


def test_store_set_operation():
    """Test set operation on store."""
    from py2mcp.util import store_to_funcs
    
    store = {}
    funcs = dict((f.__name__, f) for f in store_to_funcs(store, name='item'))
    
    funcs['set_item']('new_key', 'new_value')
    assert store['new_key'] == 'new_value'


def test_store_delete_operation():
    """Test delete operation on store."""
    from py2mcp.util import store_to_funcs
    
    store = {'to_delete': 'value'}
    funcs = dict((f.__name__, f) for f in store_to_funcs(store, name='item'))
    
    funcs['delete_item']('to_delete')
    assert 'to_delete' not in store


def test_invalid_input():
    """Test that invalid inputs raise appropriate errors."""
    with pytest.raises(TypeError):
        mk_mcp_server("not a function")
    
    with pytest.raises(TypeError):
        mk_mcp_server([lambda x: x, "not a function"])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
