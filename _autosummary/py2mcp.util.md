# py2mcp.util

Resolve object references and turn a mapping into CRUD functions.

Two small tools the builders in [`py2mcp.main`](py2mcp.main.md#module-py2mcp.main) rest on, usable on their
own: `import_object` is how `'module:function'` strings from a config file
become callables, and `store_to_funcs` is the function-level half of
[`py2mcp.mk_mcp_from_store()`](py2mcp.md#py2mcp.mk_mcp_from_store).

Main entry points:

- `import_object`: `'module.path:attr'` string to the object it names
- `store_to_funcs`: list/get/set/delete functions over a `MutableMapping`

```pycon
>>> from py2mcp.util import import_object
>>> import_object('os.path:basename')('/a/b/c.txt')
'c.txt'
```

### Functions

| [`claude_install_link`](#py2mcp.util.claude_install_link)(name, mcp_url, \*[, admin])    | Prefilled "Add custom connector" link for claude.ai.                          |
|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`import_object`](#py2mcp.util.import_object)(ref)                                 | Resolve a `'module.path:attr'` (preferred) or `'module.path.attr'` reference. |
| [`markdown_install_badge`](#py2mcp.util.markdown_install_badge)(name, mcp_url, \*[, admin]) | Markdown link that installs an MCP server as a claude.ai connector.           |
| [`store_to_funcs`](#py2mcp.util.store_to_funcs)(store, \*[, name, plural])          | Convert a MutableMapping into CRUD functions.                                 |

### py2mcp.util.claude_install_link(name, mcp_url, , admin=False)

Prefilled “Add custom connector” link for claude.ai.

There is no true one-click install for an unlisted MCP server (listing
requires Anthropic review), but this link opens the add-connector modal with
the name and URL already filled in, so the user only has to confirm — which
beats “go to Settings, find Connectors, paste this long URL”.

* **Parameters:**
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Connector name to prefill (what the user will see in their list).
  * **mcp_url** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Full URL of the MCP endpoint, e.g. `https://host/api/x/mcp`.
  * **admin** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Target the org-wide install page instead of the per-user one.
    Use it when an admin is rolling the connector out to a whole
    workspace; the default (`False`) is the personal install.
* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)
* **Returns:**
  The claude.ai URL, safe to paste into a README or a chat message.

```pycon
>>> claude_install_link('snout', 'https://example.com/api/snout_mcp/mcp')
'https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=snout&connectorUrl=https%3A%2F%2Fexample.com%2Fapi%2Fsnout_mcp%2Fmcp'
```

Names and URLs are percent-encoded, so spaces (and `&`) can’t break the
query string:

```pycon
>>> claude_install_link('my server', 'https://x.io/mcp', admin=True)
'https://claude.ai/admin-settings/connectors?modal=add-custom-connector&connectorName=my%20server&connectorUrl=https%3A%2F%2Fx.io%2Fmcp'
```

Note that the link is a convenience, not an access grant: if the server is an
OAuth resource server with an allowlist, a user who isn’t on it can follow
the link, complete the flow, and still be refused. Custom connectors are also
a paid-plan feature, so the link goes nowhere for a Free-plan user.

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
[`py2mcp.mk_mcp_from_refs()`](py2mcp.md#py2mcp.mk_mcp_from_refs): build a server from such references.

### py2mcp.util.markdown_install_badge(name, mcp_url, , admin=False)

Markdown link that installs an MCP server as a claude.ai connector.

The dominant use of [`claude_install_link()`](#py2mcp.util.claude_install_link) is pasting one into a README,
so this saves writing the same link syntax around it. Arguments are those of
[`claude_install_link()`](#py2mcp.util.claude_install_link).

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> markdown_install_badge('snout', 'https://x.io/mcp')
'[Add snout to Claude](https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=snout&connectorUrl=https%3A%2F%2Fx.io%2Fmcp)'
```

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
[`py2mcp.mk_mcp_from_store()`](py2mcp.md#py2mcp.mk_mcp_from_store): the same functions, served as MCP tools.
