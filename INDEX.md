# py2mcp - Complete Documentation Index

## Quick Navigation

### For Beginners
1. **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Start here! Overview and quick examples
2. **[GETTING_STARTED.md](GETTING_STARTED.md)** - Step-by-step setup and first server
3. **[README.md](README.md)** - Package introduction and basic usage

### For Developers
4. **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - Comprehensive API reference and patterns
5. **[examples/](examples/)** - Working code examples
   - `simple.py` - Basic usage
   - `transformations.py` - Input transformations
   - `store_example.py` - Store/CRUD patterns

### For qh Users
6. **[COMPARISON.md](COMPARISON.md)** - Detailed comparison with qh/py2http

### For Contributors
7. **[misc/CHANGELOG.md](misc/CHANGELOG.md)** - Version history and changes
8. **[py2mcp/tests/](py2mcp/tests/)** - Test suite
9. **[pyproject.toml](pyproject.toml)** - Package configuration

## Documentation Structure

```
py2mcp/
├── INDEX.md                    ← You are here
├── PROJECT_SUMMARY.md          ← Big picture overview
├── README.md                   ← Quick intro
├── GETTING_STARTED.md          ← Step-by-step setup
├── USAGE_GUIDE.md              ← Complete API reference
├── COMPARISON.md               ← py2mcp vs qh
│
├── examples/                   ← Working examples
│   ├── simple.py
│   ├── transformations.py
│   └── store_example.py
│
├── py2mcp/                     ← Source code
│   ├── __init__.py            ← Public API
│   ├── main.py                ← Core functions
│   ├── base.py                ← Base utilities
│   ├── trans.py               ← Transformations
│   ├── util.py                ← Helpers
│   └── tests/                 ← Test suite
│       └── test_basic.py
│
├── misc/
│   └── CHANGELOG.md           ← Version history
│
└── pyproject.toml             ← Package config
```

## What to Read When

### "I'm brand new to MCP"
1. Read PROJECT_SUMMARY.md (5 min)
2. Follow GETTING_STARTED.md (15 min)
3. Run examples/simple.py
4. You're ready!

### "I want to build something"
1. Skim USAGE_GUIDE.md for patterns
2. Check examples/ for similar use case
3. Copy and modify
4. Refer back to USAGE_GUIDE.md as needed

### "I'm coming from qh"
1. Read COMPARISON.md (10 min)
2. You already know the pattern!
3. Just change the imports
4. You're done

### "I want to understand everything"
1. PROJECT_SUMMARY.md - big picture
2. USAGE_GUIDE.md - all features
3. COMPARISON.md - design rationale
4. Source code - implementation details
5. Tests - usage patterns

### "I want to contribute"
1. Read source code in py2mcp/
2. Check tests in py2mcp/tests/
3. Follow coding standards in comments
4. Update CHANGELOG.md with changes

## Key Concepts

### Three Core Functions
```python
# 1. Basic server creation
mk_mcp_server(functions)

# 2. Input transformations
mk_input_trans({param: converter})

# 3. Store to CRUD
mk_mcp_from_store(mapping, name='item')
```

### The Pattern
```
Functions → mk_mcp_server → FastMCP server → run()
```

### Design Philosophy
- Simple > Complex
- Functions > Classes  
- FastMCP > Reinventing
- Patterns > Configuration
- Pythonic > Clever

## Quick Examples

### Minimal Example
```python
from py2mcp import mk_mcp_server

def add(a: int, b: int) -> int:
    return a + b

mk_mcp_server([add]).run()
```

### With Transformations
```python
from py2mcp import mk_mcp_server, mk_input_trans
import numpy as np

def process(data):
    return data.mean()

trans = mk_input_trans({'data': np.array})
mk_mcp_server([process], input_trans=trans).run()
```

### From Store
```python
from py2mcp import mk_mcp_from_store

items = {'a': 1, 'b': 2}
mk_mcp_from_store(items, name='item').run()
```

## Common Tasks

| Task | Where to Look |
|------|---------------|
| Install package | GETTING_STARTED.md |
| Create first server | GETTING_STARTED.md |
| Add transformations | USAGE_GUIDE.md, examples/transformations.py |
| Expose a dict as CRUD | USAGE_GUIDE.md, examples/store_example.py |
| Connect to Claude | GETTING_STARTED.md, USAGE_GUIDE.md |
| Test your server | USAGE_GUIDE.md |
| Understand design | COMPARISON.md, PROJECT_SUMMARY.md |
| Find examples | examples/ directory |
| Check patterns | py2mcp/tests/ |

## File Size Guide

- PROJECT_SUMMARY.md: ~300 lines - comprehensive overview
- USAGE_GUIDE.md: ~500 lines - complete reference
- COMPARISON.md: ~400 lines - detailed comparison
- GETTING_STARTED.md: ~250 lines - step-by-step guide
- README.md: ~80 lines - quick intro

Pick based on your time and needs!

## External Resources

- **FastMCP Documentation**: https://gofastmcp.com
- **MCP Specification**: https://modelcontextprotocol.io
- **FastMCP GitHub**: https://github.com/jlowin/fastmcp
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk

## Version Information

**Current Version**: 0.1.0 (Alpha)  
**Status**: Production-ready for basic usage  
**Python**: >=3.10  
**Dependencies**: FastMCP >=2.0.0  

## Support

For issues and questions:
1. Check documentation first
2. Look at examples
3. Review tests for patterns
4. Consult FastMCP docs for advanced features

## License

MIT - See project root

---

**Pro Tip**: Start with GETTING_STARTED.md if you're new, or COMPARISON.md if you know qh. Everything else is reference material you can explore as needed.

Happy building! 🚀
