"""Base objects and utilities for py2mcp."""

from typing import Callable, Iterable, Any, Mapping, Optional
from functools import wraps
from inspect import signature


def _is_method(func: Callable) -> bool:
    """Check if a callable is a bound or unbound method.
    
    >>> class MyClass:
    ...     def method(self): pass
    >>> _is_method(MyClass.method)
    False
    >>> _is_method(MyClass().method)
    True
    >>> _is_method(lambda x: x)
    False
    """
    return hasattr(func, '__self__')


def _extract_func_name(func: Callable) -> str:
    """Extract a clean function name from a callable.
    
    >>> def my_func(): pass
    >>> _extract_func_name(my_func)
    'my_func'
    """
    return getattr(func, '__name__', 'unnamed_function')


def _has_context_param(func: Callable) -> bool:
    """Check if function has a 'ctx' or 'context' parameter.
    
    This is used to detect if FastMCP's Context should be injected.
    
    >>> def func_with_ctx(x, ctx): pass
    >>> _has_context_param(func_with_ctx)
    True
    >>> def func_without_ctx(x, y): pass
    >>> _has_context_param(func_without_ctx)
    False
    """
    try:
        sig = signature(func)
        param_names = set(sig.parameters.keys())
        return 'ctx' in param_names or 'context' in param_names
    except (ValueError, TypeError):
        return False


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
