# Getting Started with py2mcp - Checklist

## Installation ✓

```bash
cd py2mcp
pip install -e .
```

**Verify installation:**
```bash
python -c "from py2mcp import mk_mcp_server; print('✓ Installation successful')"
```

## Your First MCP Server (5 minutes)

### Step 1: Create a file `my_server.py`

```python
from py2mcp import mk_mcp_server

def add(a: int, b: int) -> int:
    """Add two numbers together"""
    return a + b

def greet(name: str = "world") -> str:
    """Generate a friendly greeting"""
    return f"Hello, {name}!"

mcp = mk_mcp_server([add, greet], name="My First Server")

if __name__ == '__main__':
    mcp.run()
```

### Step 2: Test with MCP Inspector

```bash
fastmcp dev my_server.py
```

Opens at http://localhost:6274 - try calling your tools!

### Step 3: Connect to Claude Desktop

Edit your Claude Desktop config:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["/absolute/path/to/my_server.py"]
    }
  }
}
```

Restart Claude Desktop and ask it to use your tools!

## Next Steps

### ✓ Try Input Transformations

```python
from py2mcp import mk_mcp_server, mk_input_trans
import numpy as np

def stats(numbers):
    """Calculate mean and std of numbers"""
    return {
        'mean': float(numbers.mean()),
        'std': float(numbers.std())
    }

input_trans = mk_input_trans({'numbers': np.array})
mcp = mk_mcp_server([stats], input_trans=input_trans)
```

### ✓ Try Store Pattern

```python
from py2mcp import mk_mcp_from_store

todos = {
    '1': {'task': 'Learn py2mcp', 'done': True},
    '2': {'task': 'Build something cool', 'done': False}
}

mcp = mk_mcp_from_store(todos, name='todo')
# Automatically creates: list_todos, get_todo, set_todo, delete_todo
```

### ✓ Run Examples

```bash
cd py2mcp/examples

# Basic example
python simple.py

# With transformations
python transformations.py

# Store CRUD
python store_example.py
```

### ✓ Run Tests

```bash
cd py2mcp
pytest py2mcp/tests/ -v
```

Should see: ✓ 11 passed

## Common First-Time Issues

### Issue: Import Error

**Problem:** `ModuleNotFoundError: No module named 'py2mcp'`

**Solution:**
```bash
cd py2mcp
pip install -e . --break-system-packages  # If needed
```

### Issue: FastMCP Not Found

**Problem:** `ModuleNotFoundError: No module named 'fastmcp'`

**Solution:**
```bash
pip install fastmcp --break-system-packages
```

### Issue: Tools Not Showing in Claude

**Problem:** Claude can't see your tools

**Solutions:**
1. Restart Claude Desktop completely
2. Check config path is correct (absolute path!)
3. Verify server runs: `python my_server.py` (should not error)
4. Check Claude Desktop logs for errors

### Issue: Type Validation Errors

**Problem:** MCP complains about invalid inputs

**Solution:** Add proper type hints!
```python
# Bad - no type hints
def process(data):
    return data

# Good - with type hints
def process(data: list[int]) -> dict:
    return {"count": len(data)}
```

## Quick Reference

### Create Server
```python
from py2mcp import mk_mcp_server
mcp = mk_mcp_server(functions, name="Server Name")
```

### Add Transformations
```python
from py2mcp import mk_input_trans
trans = mk_input_trans({'param': converter_func})
mcp = mk_mcp_server(functions, input_trans=trans)
```

### From Store
```python
from py2mcp import mk_mcp_from_store
mcp = mk_mcp_from_store(mapping, name='item')
```

### Run Server
```python
mcp.run()  # stdio (default)
mcp.run(transport='http', port=8000)  # HTTP
mcp.run(transport='sse', port=8000)   # SSE
```

### Test Server
```bash
fastmcp dev server.py  # Inspector
pytest tests/           # Unit tests
```

## Learning Path

1. ✓ Run `examples/simple.py` - understand basics
2. ✓ Read `USAGE_GUIDE.md` - comprehensive guide
3. ✓ Check `COMPARISON.md` - if you know qh
4. ✓ Explore FastMCP docs - for advanced features
5. ✓ Build your first real tool

## Function Requirements Checklist

For each function you want to expose:

- [ ] Has type hints for parameters
- [ ] Has return type hint
- [ ] Has a docstring (becomes tool description)
- [ ] Returns JSON-serializable data
- [ ] Has a clear, descriptive name
- [ ] Does one thing well

**Example of a good function:**
```python
def calculate_discount(
    price: float,
    discount_percent: float = 10.0
) -> dict:
    """Calculate final price after discount.
    
    Args:
        price: Original price
        discount_percent: Discount percentage (default 10%)
    
    Returns:
        Dict with original price, discount, and final price
    """
    discount = price * (discount_percent / 100)
    final = price - discount
    return {
        'original': price,
        'discount': discount,
        'final': final
    }
```

## Advanced Checklist

Once comfortable with basics:

- [ ] Explored FastMCP features (resources, prompts)
- [ ] Tried middleware
- [ ] Used authentication
- [ ] Composed multiple servers
- [ ] Built a production server
- [ ] Integrated with your actual codebase

## Resources

- **FastMCP Docs:** https://gofastmcp.com
- **MCP Spec:** https://modelcontextprotocol.io
- **Examples:** `py2mcp/examples/`
- **Tests:** `py2mcp/py2mcp/tests/`

## Getting Help

1. Check `USAGE_GUIDE.md` first
2. Look at examples in `examples/`
3. Read FastMCP documentation
4. Check test files for patterns
5. Review COMPARISON.md if coming from qh

## Success Criteria

You've successfully started with py2mcp when you can:

✓ Create a basic server from functions  
✓ Test it with MCP Inspector  
✓ Connect it to Claude Desktop  
✓ Use it in a conversation with Claude  
✓ Add input transformations if needed  
✓ Understand when to use each feature  

## Congratulations! 🎉

You're now ready to build MCP servers with py2mcp.

Start simple, iterate, and build amazing tools for AI agents.

Happy coding! ✨
