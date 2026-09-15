"""Resolve object references and turn a mapping into CRUD functions.

Two small tools the builders in :mod:`py2mcp.main` rest on, usable on their
own: ``import_object`` is how ``'module:function'`` strings from a config file
become callables, and ``store_to_funcs`` is the function-level half of
:func:`py2mcp.mk_mcp_from_store`.

Main entry points:

- ``import_object``: ``'module.path:attr'`` string to the object it names
- ``store_to_funcs``: list/get/set/delete functions over a ``MutableMapping``

>>> from py2mcp.util import import_object
>>> import_object('os.path:basename')('/a/b/c.txt')
'c.txt'
"""

from importlib import import_module
from typing import Any, MutableMapping, Callable, TypeVar
from collections.abc import Iterator

KT = TypeVar("KT")
VT = TypeVar("VT")


def import_object(ref: str) -> Any:
    """Resolve a ``'module.path:attr'`` (preferred) or ``'module.path.attr'`` reference.

    Useful for building MCP servers from configuration strings (e.g. tool
    references declared in a file), so callers don't reimplement the
    ``importlib`` dance. With a colon, everything before it is the module and
    everything after it an attribute path; without one, the last dot splits
    module from attribute, so ``'pkg.mod.Class.method'`` cannot be reached in
    the dotted form (use ``'pkg.mod:Class.method'``).

    Args:
        ref: The reference string; the ``module:attr`` form is preferred.

    Returns:
        The object the reference names, after importing its module.

    Raises:
        ValueError: The reference has no module part or no attribute part.
        ImportError: The module part does not import (``ModuleNotFoundError``
            when the module does not exist; a plain ``ImportError`` if it
            exists but fails while importing).
        AttributeError: The attribute path does not exist on the module.

    Examples:

        >>> import_object('json:dumps')  # doctest: +ELLIPSIS
        <function dumps at ...>
        >>> import_object('os.path.join')  # doctest: +ELLIPSIS
        <function join at ...>
        >>> import_object('no-separator')
        Traceback (most recent call last):
            ...
        ValueError: Invalid object reference 'no-separator'; expected 'module:attr' or 'module.path.attr'.

    See Also:
        :func:`py2mcp.mk_mcp_from_refs`: build a server from such references.
    """
    if ":" in ref:
        module_name, _, attr = ref.partition(":")
    else:
        module_name, _, attr = ref.rpartition(".")
    if not module_name or not attr:
        raise ValueError(
            f"Invalid object reference {ref!r}; expected 'module:attr' "
            f"or 'module.path.attr'."
        )
    obj = import_module(module_name)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return obj


def _store_to_funcs(
    store: MutableMapping[KT, VT],
    *,
    singular: str = "item",
    plural: str = "",
) -> Iterator[tuple[str, Callable]]:
    """Generate CRUD functions from a MutableMapping.

    >>> store = {'a': 1, 'b': 2}
    >>> funcs = dict(_store_to_funcs(store, singular='item'))
    >>> sorted(funcs['list_items']())
    ['a', 'b']
    >>> funcs['get_item']('a')
    1
    """
    plural = plural or f"{singular}s"

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
        (list_items, f"list_{plural}"),
        (get_item, f"get_{singular}"),
        (set_item, f"set_{singular}"),
        (delete_item, f"delete_{singular}"),
    ]:
        func.__name__ = func_name
        yield func_name, func


def store_to_funcs(
    store: MutableMapping[KT, VT],
    *,
    name: str = "item",
    plural: str = "",
) -> list[Callable]:
    """Convert a MutableMapping into CRUD functions.

    The functions close over ``store`` and operate on it live. The list
    function takes no arguments; the others take ``key`` (and ``value`` for
    set). Set and delete return a short confirmation string.

    Args:
        store: The mapping the functions read and write.
        name: Singular noun used in the function names.
        plural: Plural noun for the list function (defaults to name + 's').

    Returns:
        The four functions, in the order list, get, set, delete, named
        ``list_<plural>``, ``get_<name>``, ``set_<name>``, ``delete_<name>``.

    Examples:

        >>> projects = {'p1': {'name': 'Project 1'}}
        >>> funcs = store_to_funcs(projects, name='project')
        >>> len(funcs)
        4
        >>> [f.__name__ for f in funcs]
        ['list_projects', 'get_project', 'set_project', 'delete_project']
        >>> list_projects, get_project, set_project, delete_project = funcs
        >>> set_project('p2', {'name': 'Project 2'})
        "Set project 'p2'"
        >>> list_projects()
        ['p1', 'p2']
        >>> delete_project('p1')
        "Deleted project 'p1'"
        >>> projects
        {'p2': {'name': 'Project 2'}}

    See Also:
        :func:`py2mcp.mk_mcp_from_store`: the same functions, served as MCP tools.
    """
    return [func for _, func in _store_to_funcs(store, singular=name, plural=plural)]
