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

## Serving: local (stdio) and remote (HTTP + OAuth)

`mk_mcp_*` build a server *object*; py2mcp also gives you two ways to **run** one.

**Local (stdio)** — for a one-click bundle (e.g. a Claude Desktop `.mcpb`):

```python
from py2mcp import serve_stdio
serve_stdio(["mypkg.tools:summarize", "mypkg.tools:translate"], name="My Tools")
# or:  python -m py2mcp --config py2mcp_config.json
```

**Remote (Streamable HTTP + OAuth 2.1)** — for a hosted MCP server reached from a
vendor's cloud (e.g. a claude.ai custom connector). The server is an OAuth 2.1
**resource server**: it *validates* a managed IdP's JWTs (audience-bound per
RFC 8707) and never issues tokens itself.

```python
from py2mcp.http import mk_http_app

AUTH = {
    "type": "jwt",                      # resource-server: validate the IdP's JWTs
    "jwks_uri": "https://idp.example.com/.well-known/jwks.json",
    "issuer": "https://idp.example.com",
    "audience": "https://my-connector.example.com/mcp",   # THIS server (RFC 8707)
    "authorization_servers": ["https://idp.example.com"],
    "base_url": "https://my-connector.example.com",
    "required_scopes": ["mcp:read"],
}

# An ASGI app you run under any ASGI server (uvicorn, gunicorn, serverless):
app = mk_http_app(["mypkg.tools:summarize"], name="My Connector", auth=AUTH)
#   uvicorn server.app:app --host 0.0.0.0 --port 8000   (behind TLS)
```

`serve_http(...)` builds and runs it in-process (FastMCP/uvicorn). Both wrap
FastMCP's native transports/OAuth — py2mcp does not reinvent them.

## License

MIT
