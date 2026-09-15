"""Input transformation for py2mcp tools: convert arguments before a function runs.

MCP clients send JSON, so a tool that wants a ``numpy`` array, a ``Path`` or a
parsed date needs its inputs converted first. ``mk_input_trans`` builds the
``input_trans`` callable that :func:`py2mcp.mk_mcp_server`,
:func:`py2mcp.mk_mcp_from_refs`, and the HTTP/stdio builders that wrap them
apply to every tool call, from a mapping of argument names to converter
functions. (``mk_mcp_from_store``'s generated CRUD tools take no
``input_trans``.)

Main entry points:

- ``mk_input_trans``: name-to-converter mapping in, ``input_trans`` callable out

>>> from py2mcp.trans import mk_input_trans
>>> trans = mk_input_trans({'n': int})
>>> trans({'n': '3', 'label': 'x'})
{'n': 3, 'label': 'x'}
"""

from typing import Callable, Mapping, Iterable, Optional, Iterator


def _name_func_pairs_from_mapping(
    name_func_relationships: Mapping,
) -> Iterator[tuple[str, Callable]]:
    """Generate (name, func) pairs from various mapping formats.

    Supports:

    - {name: func} - standard mapping
    - {name: [func1, func2]} - one name, multiple functions
    - {func: name} - reversed mapping
    - {func: [name1, name2]} - one function, multiple names

    >>> def double(x): return x * 2
    >>> list(_name_func_pairs_from_mapping({'x': double}))
    [('x', <function double at ...>)]
    """
    for k, v in name_func_relationships.items():
        if isinstance(k, str):
            name = k
            if callable(v):
                yield name, v
            elif isinstance(v, Iterable):
                for func in v:
                    if not callable(func):
                        raise TypeError(f"Expected callable, got {type(func)}")
                    yield name, func
            else:
                raise TypeError(f"Value must be callable or iterable of callables: {v}")
        elif callable(k):
            func = k
            if isinstance(v, str):
                yield v, func
            elif isinstance(v, Iterable):
                for name in v:
                    if not isinstance(name, str):
                        raise TypeError(f"Expected string, got {type(name)}")
                    yield name, func
            else:
                raise TypeError(f"Value must be string or iterable of strings: {v}")
        else:
            raise TypeError(f"Key must be string or callable: {k}")


def _to_name_func_map(name_func_relationships: Mapping) -> dict[str, Callable]:
    """Convert name-func relationships to a simple name->func mapping.

    >>> def double(x): return x * 2
    >>> _to_name_func_map({'x': double})
    {'x': <function double at ...>}
    """
    if not isinstance(name_func_relationships, Mapping):
        raise TypeError(
            f"Expected Mapping of name:func or func:name pairs, got {type(name_func_relationships)}"
        )

    pairs = list(_name_func_pairs_from_mapping(name_func_relationships))
    result = dict(pairs)

    if len(result) != len(pairs):
        raise ValueError("Duplicate names found in relationships")

    return result


def _apply_transformations(
    kwargs: dict, name_func_map: Mapping[str, Callable]
) -> Iterator[tuple[str, any]]:
    """Apply transformations to matching kwargs.

    >>> def double(x): return x * 2
    >>> transforms = {'a': double}
    >>> dict(_apply_transformations({'a': 5, 'b': 10}, transforms))
    {'a': 10, 'b': 10}
    """
    for name, value in kwargs.items():
        if name in name_func_map:
            yield name, name_func_map[name](value)
        else:
            yield name, value


def mk_input_trans(
    name_func_relationships: Optional[Mapping] = None,
) -> Callable[[dict], dict]:
    """Create an input transformation function from name->func mappings.

    The returned callable takes a tool call's keyword arguments as a dict and
    returns a new dict in which each named argument has been passed through its
    converter; arguments with no converter are copied through unchanged. Pass it
    as ``input_trans`` to :func:`py2mcp.mk_mcp_server` and friends.

    Args:
        name_func_relationships: Which converter applies to which argument, as
            ``{name: func}``, or reversed as ``{func: name}`` or
            ``{func: [name, ...]}`` when one converter serves several arguments.
            ``None`` gives a transformation that only copies the dict.

    Returns:
        A function from a kwargs dict to a new kwargs dict.

    Raises:
        ValueError: The same argument name is mapped more than once.

    Examples:

        >>> def to_int(x): return int(x)
        >>> trans = mk_input_trans({'x': to_int})
        >>> trans({'x': '42', 'y': 'hello'})
        {'x': 42, 'y': 'hello'}

        One converter for several arguments, written the reversed way:

        >>> trans = mk_input_trans({to_int: ['x', 'y']})
        >>> trans({'x': '1', 'y': '2', 'z': '3'})
        {'x': 1, 'y': 2, 'z': '3'}

        No mapping means no conversion:

        >>> mk_input_trans()({'x': '1'})
        {'x': '1'}

    See Also:
        :func:`py2mcp.mk_mcp_server`: where the returned callable is applied.
    """
    if name_func_relationships is None:
        return lambda kwargs: dict(kwargs)

    name_func_map = _to_name_func_map(name_func_relationships)

    def input_trans(kwargs: dict) -> dict:
        """Transform input kwargs according to the mapping."""
        return dict(_apply_transformations(kwargs, name_func_map))

    return input_trans
