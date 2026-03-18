# CHANGELOG

## 2025-10-23 - Initial Release

### Added
- Created `py2mcp` package structure following standard Python package layout
- Implemented `mk_mcp_server()` - main function to create MCP servers from Python functions
- Implemented `mk_mcp_from_store()` - create MCP servers from MutableMapping objects
- Implemented `mk_input_trans()` - create input transformation functions
- Added support for automatic CRUD operations from stores (list, get, set, delete)
- Built on FastMCP 2.0 as the underlying MCP framework
- Created comprehensive examples:
  - `simple.py` - basic function-to-MCP conversion
  - `transformations.py` - input transformation with numpy arrays
  - `store_example.py` - MutableMapping to CRUD operations
- Added test suite with pytest
- Followed architectural preferences:
  - Functional over OOP where appropriate
  - Small, focused helper functions with underscore prefix
  - Dataclass-ready structure (though not needed yet)
  - Minimal docstrings with doctests where practical
  - Generator-based utilities for memory efficiency

### Architecture Decisions
- Used FastMCP as foundation rather than reinventing MCP protocol implementation
- Followed the `qh` (py2http) pattern: simple function list → server object
- Separated concerns into modules: base, trans, util, main
- Input transformations follow same pattern as qh's HTTP transformations
- Store pattern follows Mapping/MutableMapping facade approach

### Notes
- This is a thin, Pythonic wrapper around FastMCP
- Focuses on simplicity and following established patterns from py2http/qh
- All core functionality working and tested
