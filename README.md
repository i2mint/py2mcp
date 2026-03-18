# py2mcp

Quick MCP (Model Context Protocol) server creation from Python functions.

## Installation

```bash
pip install py2mcp
```

## Quick Start

```python
from py2mcp import mk_mcp_server

def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

def greet(name: str = "world") -> str:
    """Greet someone"""
    return f"Hello, {name}!"

# Create and run MCP server
mcp = mk_mcp_server([add, greet])

if __name__ == '__main__':
    mcp.run()
```

That's it! Your functions are now available as MCP tools.

## Features

- **Simple**: Just pass functions to `mk_mcp_server()`
- **Flexible**: Supports input/output transformations
- **Pythonic**: Clean, decorator-free function definitions
- **Powerful**: Built on FastMCP for production-ready servers

## Input Transformations

Transform inputs before they reach your functions:

```python
from py2mcp import mk_mcp_server, mk_input_trans
import numpy as np

def add_arrays(a, b):
    """Add two numpy arrays"""
    return (a + b).tolist()

# Convert list inputs to numpy arrays
input_trans = mk_input_trans({'a': np.array, 'b': np.array})
mcp = mk_mcp_server([add_arrays], input_trans=input_trans)
```

## From Stores (MutableMapping)

Automatically expose CRUD operations from any mapping:

```python
from py2mcp import mk_mcp_from_store

projects = {'proj1': {'name': 'Project 1'}, 'proj2': {'name': 'Project 2'}}
mcp = mk_mcp_from_store(projects, name="project")

# Automatically creates: list_projects, get_project, set_project, delete_project
```

## License

MIT
