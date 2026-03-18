"""Base objects and utilities for py2mcp."""

from typing import Callable, Iterable, Any, Optional
from functools import wraps


def _wrap_with_input_trans(func: Callable, input_trans: Optional[Callable]) -> Callable:
    """Wrap a function to apply input transformation.
    
    >>> def double(x): return x * 2
    >>> def add_one_trans(kwargs): return {k: v + 1 for k, v in kwargs.items()}
    >>> wrapped = _wrap_with_input_trans(double, add_one_trans)
    >>> wrapped(x=5)
    12
    """
    if input_trans is None:
        return func
    
    @wraps(func)
    def wrapper(**kwargs):
        transformed = input_trans(kwargs)
        return func(**transformed)
    
    # Preserve original function metadata for introspection
    wrapper.__wrapped__ = func
    return wrapper


def _normalize_to_iterable(funcs: Any) -> Iterable[Callable]:
    """Normalize input to an iterable of callables.
    
    >>> def f(): pass
    >>> def g(): pass
    >>> list(_normalize_to_iterable(f))
    [<function f at ...>]
    >>> len(list(_normalize_to_iterable([f, g])))
    2
    """
    if callable(funcs):
        return [funcs]
    elif isinstance(funcs, Iterable):
        result = list(funcs)
        if not all(callable(f) for f in result):
            raise TypeError("All items must be callable")
        return result
    else:
        raise TypeError(f"Expected callable or iterable of callables, got {type(funcs)}")
