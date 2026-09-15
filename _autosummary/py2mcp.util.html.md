# py2mcp.util

Resolve object references and turn a mapping into CRUD functions.

Two small tools the builders in [`py2mcp.main`](py2mcp.main.html.md#module-py2mcp.main) rest on, usable on their
own: `import_object` is how `'module:function'` strings from a config file
become callables, and `store_to_funcs` is the function-level half of
[`py2mcp.mk_mcp_from_store()`](py2mcp.html.md#py2mcp.mk_mcp_from_store).

Main entry points:

- `import_object`: `'module.path:attr'` string to the object it names
- `store_to_funcs`: list/get/set/delete functions over a `MutableMapping`

```pycon
>>> from py2mcp.util import import_object
>>> import_object('os.path:basename')('/a/b/c.txt')
'c.txt'
```

### Functions

| [`import_object`](#py2mcp.util.import_object)(ref)                        | Resolve a `'module.path:attr'` (preferred) or `'module.path.attr'` reference.   |
|--------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| [`store_to_funcs`](#py2mcp.util.store_to_funcs)(store, \*[, name, plural]) | Convert a MutableMapping into CRUD functions.                                   |

### py2mcp.util.import_object(ref)

Resolve a `'module.path:attr'` (preferred) or `'module.path.attr'` reference.

Useful for building MCP servers from configuration strings (e.g. tool
references declared in a file), so callers don’t reimplement the
`importlib` dance. With a colon, everything before it is the module and
everything after it an attribute path; without one, the last dot splits
module from attribute, so `'pkg.mod.Class.method'` cannot be reached in
the dotted form (use `'pkg.mod:Class.method'`).

* **Parameters:**
  **ref** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The reference string; the `module:attr` form is preferred.
* **Return type:**
  [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)
* **Returns:**
  The object the reference names, after importing its module.
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – The reference has no module part or no attribute part.
  * [**ImportError**](https://docs.python.org/3/builtins/exceptions.html#ImportError) – The module part does not import (`ModuleNotFoundError`
        when the module does not exist; a plain `ImportError` if it
        exists but fails while importing).
  * [**AttributeError**](https://docs.python.org/3/builtins/exceptions.html#AttributeError) – The attribute path does not exist on the module.

### Examples

```pycon
>>> import_object('json:dumps')
<function dumps at ...>
>>> import_object('os.path.join')
<function join at ...>
>>> import_object('no-separator')
Traceback (most recent call last):
    ...
ValueError: Invalid object reference 'no-separator'; expected 'module:attr' or 'module.path.attr'.
```

#### SEE ALSO
[`py2mcp.mk_mcp_from_refs()`](py2mcp.html.md#py2mcp.mk_mcp_from_refs): build a server from such references.

### py2mcp.util.store_to_funcs(store, , name='item', plural='')

Convert a MutableMapping into CRUD functions.

The functions close over `store` and operate on it live. The list
function takes no arguments; the others take `key` (and `value` for
set). Set and delete return a short confirmation string.

* **Parameters:**
  * **store** ([`MutableMapping`](https://docs.python.org/3/library/typing.html#typing.MutableMapping)[[`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`KT`), [`TypeVar`](https://docs.python.org/3/library/typing.html#typing.TypeVar)(`VT`)]) – The mapping the functions read and write.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Singular noun used in the function names.
  * **plural** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Plural noun for the list function (defaults to name + ‘s’).
* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)]
* **Returns:**
  The four functions, in the order list, get, set, delete, named
  `list_<plural>`, `get_<name>`, `set_<name>`, `delete_<name>`.

### Examples

```pycon
>>> projects = {'p1': {'name': 'Project 1'}}
>>> funcs = store_to_funcs(projects, name='project')
>>> len(funcs)
4
>>> [f.__name__ for f in funcs]
['list_projects', 'get_project', 'set_project', 'delete_project']
>>> list_projects, get_project, set_project, delete_project = funcs
>>> set_project('p2', {'name': 'Project 2'})
"Set project 'p2'"
>>> list_projects()
['p1', 'p2']
>>> delete_project('p1')
"Deleted project 'p1'"
>>> projects
{'p2': {'name': 'Project 2'}}
```

#### SEE ALSO
[`py2mcp.mk_mcp_from_store()`](py2mcp.html.md#py2mcp.mk_mcp_from_store): the same functions, served as MCP tools.
