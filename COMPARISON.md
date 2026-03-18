# py2mcp vs qh (py2http) - Pattern Comparison

This document shows how `py2mcp` follows the same design patterns as `qh` (the HTTP service builder), making it familiar and intuitive.

## Core Pattern: Functions → Server

### qh (HTTP)
```python
from qh import mk_http_service_app

def add(a: int, b: int) -> int:
    return a + b

app = mk_http_service_app([add])
app.run()
```

### py2mcp (MCP)
```python
from py2mcp import mk_mcp_server

def add(a: int, b: int) -> int:
    return a + b

mcp = mk_mcp_server([add])
mcp.run()
```

**Identical pattern!** Pass functions, get a server.

## Input Transformations

### qh (HTTP)
```python
from qh import mk_http_service_app
from qh.trans import mk_json_handler_from_name_mapping
import numpy as np

def add_arrays(a, b):
    return (a + b).tolist()

input_trans = mk_json_handler_from_name_mapping({
    'a': np.array,
    'b': np.array
})

app = mk_http_service_app([add_arrays], input_trans=input_trans)
```

### py2mcp (MCP)
```python
from py2mcp import mk_mcp_server, mk_input_trans
import numpy as np

def add_arrays(a, b):
    return (a + b).tolist()

input_trans = mk_input_trans({
    'a': np.array,
    'b': np.array
})

mcp = mk_mcp_server([add_arrays], input_trans=input_trans)
```

**Same transformation pattern!** Map parameter names to conversion functions.

## Store/Mapping Dispatch

### qh (HTTP) - Conceptual
```python
# qh has store dispatch patterns (see scrap/store_dispatch_*.py)
# where a MutableMapping is exposed via HTTP endpoints

from qh.scrap.store_dispatch_1 import StoreAccess

store = StoreAccess.from_uri('test_uri')
# Exposes: list(), read(), write(), delete()
```

### py2mcp (MCP)
```python
from py2mcp import mk_mcp_from_store

projects = {'proj1': {...}, 'proj2': {...}}

mcp = mk_mcp_from_store(projects, name='project')
# Automatically creates:
# - list_projects()
# - get_project(key)
# - set_project(key, value)
# - delete_project(key)
```

**Same CRUD pattern!** Automatically generate operations from stores.

## Architecture Parallels

| Aspect | qh (py2http) | py2mcp |
|--------|--------------|---------|
| **Foundation** | py2http (bottle/FastAPI) | FastMCP |
| **Philosophy** | Don't reinvent HTTP | Don't reinvent MCP |
| **Main Function** | `mk_http_service_app()` | `mk_mcp_server()` |
| **Transformation** | `mk_json_handler_from_name_mapping()` | `mk_input_trans()` |
| **Store Support** | Store dispatch examples | `mk_mcp_from_store()` |
| **Return Type** | HTTP app object | FastMCP object |
| **Run Method** | `app.run()` | `mcp.run()` |

## Module Structure Comparison

### qh Structure
```
qh/
├── __init__.py          # Exports: mk_http_service_app
├── main.py              # Core app creation
├── trans.py             # Transformations
├── util.py              # Helpers (flat_callable_for, etc.)
└── scrap/               # WIP patterns
```

### py2mcp Structure
```
py2mcp/
├── __init__.py          # Exports: mk_mcp_server, mk_input_trans, mk_mcp_from_store
├── main.py              # Core server creation
├── trans.py             # Transformations
├── util.py              # Helpers (store_to_funcs, etc.)
└── tests/               # Test suite
```

**Nearly identical organization!**

## Implementation Details

### Function Flattening

Both packages handle methods and functions uniformly:

#### qh
```python
# from qh.util import flat_callable_for
def flat_callable_for(func, func_name=None, cls=None):
    """Flatten cls->instance->method call pipeline"""
    containing_cls = get_class_that_defined_method(func)
    if not containing_cls:
        return func  # Already flat
    # ... flatten the method
```

#### py2mcp
```python
# from py2mcp.base import _normalize_to_iterable
def _normalize_to_iterable(funcs):
    """Normalize input to an iterable of callables"""
    if callable(funcs):
        return [funcs]
    elif isinstance(funcs, Iterable):
        return list(funcs)
    # ... validate
```

### Transformation Pipeline

Both use the same pattern: **name → function mapping**

#### qh
```python
def transform_mapping_vals_with_name_func_map(mapping, name_func_map):
    for name, val in mapping.items():
        if name in name_func_map:
            yield name, name_func_map[name](val)
        else:
            yield name, val
```

#### py2mcp
```python
def _apply_transformations(kwargs, name_func_map):
    for name, value in kwargs.items():
        if name in name_func_map:
            yield name, name_func_map[name](value)
        else:
            yield name, value
```

**Identical logic!**

## Key Differences

While the patterns are the same, there are protocol differences:

| Feature | HTTP (qh) | MCP (py2mcp) |
|---------|-----------|--------------|
| **Transport** | HTTP endpoints | Stdio/HTTP/SSE |
| **Client** | curl, browsers | Claude, Cursor, MCP clients |
| **Method Types** | GET/POST/PUT/DELETE | Tools/Resources/Prompts |
| **Request Format** | JSON body, URL params | JSON-RPC |
| **Response Format** | JSON response | Structured tool results |

## Usage Comparison

### Starting a Server

#### qh
```python
# HTTP server on port 8080
if __name__ == '__main__':
    app.run(port=8080)
```

Test with:
```bash
curl -X POST http://localhost:8080/add \
  -H "Content-Type: application/json" \
  -d '{"a": 3, "b": 5}'
```

#### py2mcp
```python
# Stdio server (default) or HTTP
if __name__ == '__main__':
    mcp.run()  # stdio
    # mcp.run(transport='http', port=8000)  # http
```

Test with:
```bash
fastmcp dev server.py  # Opens web inspector
```

### Function Requirements

Both require:
- Type hints (for schema generation)
- Docstrings (for documentation)
- JSON-serializable returns

```python
# Works in both qh and py2mcp
def process_data(
    text: str,
    count: int = 10,
    uppercase: bool = False
) -> dict:
    """Process text data.
    
    Args:
        text: Input text
        count: Max length
        uppercase: Convert to uppercase
    
    Returns:
        Processed result
    """
    result = text[:count]
    if uppercase:
        result = result.upper()
    return {"result": result, "length": len(result)}
```

## Migration Guide: HTTP → MCP

If you have a qh HTTP service and want to make it an MCP server:

1. **Change import**:
   ```python
   # from qh import mk_http_service_app
   from py2mcp import mk_mcp_server
   ```

2. **Change function name**:
   ```python
   # app = mk_http_service_app([...])
   mcp = mk_mcp_server([...])
   ```

3. **Update transformations** (if used):
   ```python
   # from qh.trans import mk_json_handler_from_name_mapping
   from py2mcp import mk_input_trans
   
   # input_trans = mk_json_handler_from_name_mapping({...})
   input_trans = mk_input_trans({...})
   ```

4. **Change run call**:
   ```python
   # app.run(port=8080)
   mcp.run()  # or mcp.run(transport='http', port=8000)
   ```

That's it! Your functions stay exactly the same.

## When to Use Which?

### Use qh (py2http) when:
- You need HTTP/REST endpoints
- Building a web API
- Want browser/curl access
- Integrating with HTTP clients

### Use py2mcp when:
- Building AI agent tools
- Integrating with Claude/Cursor
- Want LLM-friendly interfaces
- Following MCP standard

### Use both when:
- You want both HTTP and MCP access
- Maximum flexibility
- Different client types

```python
from qh import mk_http_service_app
from py2mcp import mk_mcp_server

# Same functions, two servers!
funcs = [add, multiply, greet]

http_app = mk_http_service_app(funcs)
mcp_server = mk_mcp_server(funcs)
```

## Design Philosophy

Both packages follow the same principles:

1. **Simplicity**: Minimal API surface
2. **Convention over configuration**: Sensible defaults
3. **Don't reinvent**: Build on proven frameworks
4. **Pythonic**: Feels natural to Python developers
5. **Functional**: Prefer functions over classes
6. **SSOT**: Single source of truth (the functions)
7. **Open/closed**: Easy to extend, works out of the box

## Conclusion

`py2mcp` is essentially "qh for MCP" - the same clean, simple pattern applied to a different protocol. If you liked how qh worked, you'll feel right at home with py2mcp.

The key insight: **Functions are the universal interface.** Whether exposing them via HTTP or MCP, the pattern is the same:

```
functions → wrapper → server → run
```

Simple, clean, Pythonic. ✨
