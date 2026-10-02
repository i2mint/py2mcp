# py2mcp.base

Private helpers shared by the builders in [`py2mcp.main`](py2mcp.main.html.md#module-py2mcp.main).

Argument normalization (`funcs` and `middleware` accept one object or an
iterable) and the wrapper that applies an `input_trans` to a tool’s keyword
arguments before the function runs. Nothing here is part of the public API.

### Module Attributes

| [`normalize_middleware`](#py2mcp.base.normalize_middleware)(middleware)   | Public name for `_normalize_middleware()`, for hosts (`enlace_connector`) that compose middleware lists before handing them to a builder.   |
|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|

### Functions

| [`normalize_middleware`](#py2mcp.base.normalize_middleware)(middleware)   | Public name for `_normalize_middleware()`, for hosts (`enlace_connector`) that compose middleware lists before handing them to a builder.   |
|-------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|

### py2mcp.base.normalize_middleware(middleware)

Public name for `_normalize_middleware()`, for hosts (`enlace_connector`)
that compose middleware lists before handing them to a builder.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`list`](https://docs.python.org/3/builtins/stdtypes.html#list)]
