"""General utilities for py2mcp."""

from typing import MutableMapping, Callable, TypeVar
from collections.abc import Iterator

KT = TypeVar('KT')
VT = TypeVar('VT')


def _store_to_funcs(
    store: MutableMapping[KT, VT],
    *,
    singular: str = 'item',
    plural: str = '',
) -> Iterator[tuple[str, Callable]]:
    """Generate CRUD functions from a MutableMapping.

    >>> store = {'a': 1, 'b': 2}
    >>> funcs = dict(_store_to_funcs(store, singular='item'))
    >>> sorted(funcs['list_items']())
    ['a', 'b']
    >>> funcs['get_item']('a')
    1
    """
    plural = plural or f'{singular}s'

    def list_items() -> list[KT]:
        """List all keys."""
        return list(store.keys())

    def get_item(key: KT) -> VT:
        """Get a value by key."""
        return store[key]

    def set_item(key: KT, value: VT) -> str:
        """Set a value."""
        store[key] = value
        return f"Set {singular} '{key}'"

    def delete_item(key: KT) -> str:
        """Delete a value."""
        del store[key]
        return f"Deleted {singular} '{key}'"

    for func, func_name in [
        (list_items, f'list_{plural}'),
        (get_item, f'get_{singular}'),
        (set_item, f'set_{singular}'),
        (delete_item, f'delete_{singular}'),
    ]:
        func.__name__ = func_name
        yield func_name, func


def store_to_funcs(
    store: MutableMapping[KT, VT],
    *,
    name: str = 'item',
    plural: str = '',
) -> list[Callable]:
    """Convert a MutableMapping into CRUD functions.

    >>> projects = {'p1': {'name': 'Project 1'}}
    >>> funcs = store_to_funcs(projects, name='project')
    >>> len(funcs)
    4
    >>> [f.__name__ for f in funcs]
    ['list_projects', 'get_project', 'set_project', 'delete_project']
    """
    return [func for _, func in _store_to_funcs(store, singular=name, plural=plural)]
