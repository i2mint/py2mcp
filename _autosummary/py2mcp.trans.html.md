# py2mcp.trans

Input transformation for py2mcp tools: convert arguments before a function runs.

MCP clients send JSON, so a tool that wants a `numpy` array, a `Path` or a
parsed date needs its inputs converted first. `mk_input_trans` builds the
`input_trans` callable that [`py2mcp.mk_mcp_server()`](py2mcp.html.md#py2mcp.mk_mcp_server),
[`py2mcp.mk_mcp_from_refs()`](py2mcp.html.md#py2mcp.mk_mcp_from_refs), and the HTTP/stdio builders that wrap them
apply to every tool call, from a mapping of argument names to converter
functions. (`mk_mcp_from_store`’s generated CRUD tools take no
`input_trans`.)

Main entry points:

- `mk_input_trans`: name-to-converter mapping in, `input_trans` callable out

```pycon
>>> from py2mcp.trans import mk_input_trans
>>> trans = mk_input_trans({'n': int})
>>> trans({'n': '3', 'label': 'x'})
{'n': 3, 'label': 'x'}
```

### Functions

| [`mk_input_trans`](#py2mcp.trans.mk_input_trans)([name_func_relationships])   | Create an input transformation function from name->func mappings.   |
|----------------------------------------------------------------------------------------------|---------------------------------------------------------------------|

### py2mcp.trans.mk_input_trans(name_func_relationships=None)

Create an input transformation function from name->func mappings.

The returned callable takes a tool call’s keyword arguments as a dict and
returns a new dict in which each named argument has been passed through its
converter; arguments with no converter are copied through unchanged. Pass it
as `input_trans` to [`py2mcp.mk_mcp_server()`](py2mcp.html.md#py2mcp.mk_mcp_server) and friends.

* **Parameters:**
  **name_func_relationships** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)]) – Which converter applies to which argument, as
  `{name: func}`, or reversed as `{func: name}` or
  `{func: [name, ...]}` when one converter serves several arguments.
  `None` gives a transformation that only copies the dict.
* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]
* **Returns:**
  A function from a kwargs dict to a new kwargs dict.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – The same argument name is mapped more than once.

### Examples

```pycon
>>> def to_int(x): return int(x)
>>> trans = mk_input_trans({'x': to_int})
>>> trans({'x': '42', 'y': 'hello'})
{'x': 42, 'y': 'hello'}
```

One converter for several arguments, written the reversed way:

```pycon
>>> trans = mk_input_trans({to_int: ['x', 'y']})
>>> trans({'x': '1', 'y': '2', 'z': '3'})
{'x': 1, 'y': 2, 'z': '3'}
```

No mapping means no conversion:

```pycon
>>> mk_input_trans()({'x': '1'})
{'x': '1'}
```

#### SEE ALSO
[`py2mcp.mk_mcp_server()`](py2mcp.html.md#py2mcp.mk_mcp_server): where the returned callable is applied.
