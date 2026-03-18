# py2mcp - Usage Guide

## Overview

`py2mcp` is a lightweight, Pythonic wrapper around FastMCP that lets you create Model Context Protocol (MCP) servers from ordinary Python functions. It follows the same pattern as `qh` (py2http) - give it functions, get a server.

## Installation

```bash
cd py2mcp
pip install -e .
```

Or when published:
```bash
pip install py2mcp
```

## Quick Start

### Basic Example

```python
from py2mcp import mk_mcp_server

def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

def greet(name: str = "world") -> str:
    """Greet someone"""
    return f"Hello, {name}!"

# Create MCP server
mcp = mk_mcp_server([add, greet], name="My Server")

if __name__ == '__main__':
    mcp.run()
```

That's it! Your functions are now MCP tools.

## Key Features

### 1. Simple Function-to-Tool Conversion

Just pass functions (or a single function) to `mk_mcp_server()`:

```python
# Single function
mcp = mk_mcp_server(add)

# Multiple functions
mcp = mk_mcp_server([add, multiply, divide])
```

The functions are automatically:
- Registered as MCP tools
- Documented using their docstrings
- Schema-validated using type hints

### 2. Input Transformations

Transform inputs before they reach your functions (just like qh):

```python
from py2mcp import mk_mcp_server, mk_input_trans
import numpy as np

def add_arrays(a, b):
    """Add two arrays element-wise"""
    return (a + b).tolist()

# Convert list inputs to numpy arrays
input_trans = mk_input_trans({
    'a': np.array,
    'b': np.array
})

mcp = mk_mcp_server([add_arrays], input_trans=input_trans)
```

The `mk_input_trans()` function takes a mapping of `{param_name: transform_func}` and returns a transformation function.

### 3. Store (MutableMapping) to CRUD

Automatically expose any dict-like object as CRUD operations:

```python
from py2mcp import mk_mcp_from_store

projects = {
    'proj1': {'name': 'Website', 'status': 'active'},
    'proj2': {'name': 'Mobile App', 'status': 'planning'}
}

# Automatically creates: list_projects, get_project, set_project, delete_project
mcp = mk_mcp_from_store(projects, name='project')
```

This generates four tools:
- `list_projects()` - list all keys
- `get_project(key)` - get an item
- `set_project(key, value)` - create/update an item
- `delete_project(key)` - delete an item

## Running Your Server

### Stdio Mode (Default)

```bash
python your_server.py
```

This runs in stdio mode, which is what Claude Desktop and other MCP clients use.

### HTTP Mode

```python
if __name__ == '__main__':
    mcp.run(transport='http', port=8000)
```

Then access at `http://localhost:8000/mcp`

### SSE Mode

```python
if __name__ == '__main__':
    mcp.run(transport='sse', port=8000)
```

### Testing with MCP Inspector

FastMCP includes a built-in testing interface:

```bash
fastmcp dev your_server.py
```

This opens an interactive web interface at http://localhost:6274 for testing your tools.

## Integration with Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/absolute/path/to/your_server.py"]
    }
  }
}
```

### Config Location

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

## Architecture

### Module Structure

```
py2mcp/
├── __init__.py       # Public API: mk_mcp_server, mk_mcp_from_store, mk_input_trans
├── main.py           # Core server creation functions
├── base.py           # Base utilities and helpers
├── trans.py          # Input transformation utilities
├── util.py           # Store/mapping helpers
└── tests/            # Test suite
```

### Design Principles

Following your coding standards:

1. **Functional over OOP** - Uses functions and transformations, not heavy class hierarchies
2. **Single Source of Truth** - FastMCP is the foundation, we don't reimplement
3. **Minimal boilerplate** - Just pass functions, get a server
4. **Helper functions** - Small, focused utilities with `_` prefix for internal use
5. **Generator-based** - Uses iterators where appropriate for memory efficiency
6. **Docstrings + Doctests** - Every function documented with simple tests

## Advanced Usage

### Custom FastMCP Features

Since `mk_mcp_server()` returns a FastMCP instance, you can use all FastMCP features:

```python
mcp = mk_mcp_server([add, multiply])

# Add resources
@mcp.resource("config://settings")
def get_settings():
    return {"version": "1.0"}

# Add prompts
@mcp.prompt()
def code_review_prompt(code: str):
    return f"Please review this code: {code}"

# Add middleware
@mcp.middleware()
async def logging_middleware(request, call_next):
    print(f"Request: {request}")
    return await call_next(request)

# Run with authentication
mcp.run(auth="your-api-key")
```

### Combining Multiple Servers

You can mount multiple py2mcp servers together:

```python
math_mcp = mk_mcp_server([add, multiply], name="Math")
text_mcp = mk_mcp_server([greet, format_text], name="Text")

# Mount text into math
math_mcp.mount(text_mcp, prefix="/text")
```

### Testing Your Server

```python
import asyncio
from fastmcp import Client

async def test():
    mcp = mk_mcp_server([add])
    
    async with Client(mcp) as client:
        result = await client.call_tool("add", {"a": 5, "b": 3})
        print(result)  # 8

asyncio.run(test())
```

## Comparison to py2http (qh)

If you're familiar with `qh`, here's the mapping:

| qh (HTTP) | py2mcp (MCP) |
|-----------|--------------|
| `mk_http_service_app(funcs)` | `mk_mcp_server(funcs)` |
| `input_trans` parameter | `input_trans` parameter |
| `mk_json_handler_from_name_mapping()` | `mk_input_trans()` |
| Store dispatch | `mk_mcp_from_store()` |
| FastAPI backend | FastMCP backend |
| HTTP endpoints | MCP tools |

The pattern is nearly identical!

## Examples

See the `examples/` directory:

- `simple.py` - Basic function conversion
- `transformations.py` - Input transformation with numpy
- `store_example.py` - MutableMapping to CRUD

Run them with:
```bash
python examples/simple.py
```

## Testing

Run the test suite:
```bash
pytest py2mcp/tests/
```

Run doctests:
```bash
python -m doctest py2mcp/*.py -v
```

## Next Steps

1. **Create your functions** - Write normal Python functions
2. **Add type hints** - MCP uses them for validation
3. **Add docstrings** - They become tool descriptions
4. **Call mk_mcp_server()** - Pass your functions
5. **Run it** - Start serving!

## Tips

- **Type hints matter**: MCP uses them to validate inputs
- **Docstrings are descriptions**: They help LLMs understand your tools
- **Keep functions focused**: Each function = one tool
- **Use input transformations**: When you need type conversions
- **Test with Inspector**: `fastmcp dev` is your friend

## Troubleshooting

### Import Errors
```bash
pip install -e .  # Reinstall in editable mode
```

### Server Won't Start
- Check you're calling `mcp.run()` not just creating the instance
- Ensure no other process is using the port (for HTTP/SSE)

### Tools Not Showing Up
- Verify functions are passed to `mk_mcp_server()`
- Check for exceptions during server creation
- Use `fastmcp dev` to test

### Type Validation Errors
- Add proper type hints to your functions
- Check inputs match expected types
- Use input transformations for conversions

## Resources

- FastMCP Documentation: https://gofastmcp.com
- MCP Specification: https://modelcontextprotocol.io
- Example Servers: https://github.com/modelcontextprotocol/servers

## License

MIT
