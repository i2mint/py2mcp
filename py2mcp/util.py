"""General utilities for py2mcp."""

from typing import MutableMapping, Mapping, Any, Callable, TypeVar
from collections.abc import Iterator

KT = TypeVar('KT')
VT = TypeVar('VT')


def _store_to_funcs(
    store: MutableMapping[KT, VT], *, prefix: str = ''
) -> Iterator[tuple[str, Callable]]:
    """Generate CRUD functions from a MutableMapping.
    
    >>> store = {'a': 1, 'b': 2}
    >>> funcs = dict(_store_to_funcs(store, prefix='items'))
    >>> funcs['list_items']()
    ['a', 'b']
    >>> funcs['get_items']('a')
    1
    """
    name_base = prefix if prefix else 'item'
    
    def list_items() -> list[KT]:
        f"""List all {name_base}s"""
        return list(store.keys())
    
    def get_item(key: KT) -> VT:
        f"""Get a {name_base} by key"""
        return store[key]
    
    def set_item(key: KT, value: VT) -> str:
        f"""Set a {name_base}"""
        store[key] = value
        return f"Set {name_base} '{key}'"
    
    def delete_item(key: KT) -> str:
        f"""Delete a {name_base}"""
        del store[key]
        return f"Deleted {name_base} '{key}'"
    
    # Set proper names
    list_items.__name__ = f'list_{name_base}s'
    get_item.__name__ = f'get_{name_base}'
    set_item.__name__ = f'set_{name_base}'
    delete_item.__name__ = f'delete_{name_base}'
    
    yield list_items.__name__, list_items
    yield get_item.__name__, get_item
    yield set_item.__name__, set_item
    yield delete_item.__name__, delete_item


def store_to_funcs(
    store: MutableMapping[KT, VT], *, name: str = 'item'
) -> list[Callable]:
    """Convert a MutableMapping into CRUD functions.
    
    >>> projects = {'p1': {'name': 'Project 1'}}
    >>> funcs = store_to_funcs(projects, name='project')
    >>> len(funcs)
    4
    >>> [f.__name__ for f in funcs]
    ['list_projects', 'get_project', 'set_project', 'delete_project']
    """
    return [func for _, func in _store_to_funcs(store, prefix=name)]
