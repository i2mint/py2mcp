# py2mcp.serve

Serve a py2mcp `FastMCP` server over stdio, as a packaged integration launches it.

[`py2mcp.mk_mcp_server()`](py2mcp.md#py2mcp.mk_mcp_server) / [`py2mcp.mk_mcp_from_refs()`](py2mcp.md#py2mcp.mk_mcp_from_refs) build a server
*object* but deliberately leave *running* it to the caller (the only run hint in
`main` is a comment). This module adds the thin “actually serve it over stdio”
layer plus a small JSON-config loader, so a one-click bundle (e.g. a Claude
Desktop `.mcpb` Desktop Extension) can point its `manifest.json` at:

```default
python -m py2mcp --config ${__dirname}/server/py2mcp_config.json
```

and get a live MCP server. The config is just `{"name": ..., "refs": [...]}`
where each ref is a `'module:function'` string resolved by
[`py2mcp.util.import_object()`](py2mcp.util.md#py2mcp.util.import_object).

stdio note: an MCP stdio server speaks newline-delimited JSON-RPC on
stdout, so nothing else may be written there. `FastMCP`’s `run` handles this;
keep application logging on stderr.

Main entry points:

- `serve_stdio`: build from refs and run over stdio (blocking)
- `resolve_server_config`: merge a config file with explicit refs and name
- `load_server_config`: read and check the JSON config
- `main`: the `python -m py2mcp` command line

```pycon
>>> from py2mcp.serve import resolve_server_config
>>> resolve_server_config(refs=['os.path:basename'])
(['os.path:basename'], 'py2mcp Server')
```

### Module Attributes

| [`DFLT_SERVER_NAME`](#py2mcp.serve.DFLT_SERVER_NAME)   | Default server name when neither a config nor `--name` supplies one.   |
|---------------------------------------------------------------------|------------------------------------------------------------------------|

### Functions

| [`load_server_config`](#py2mcp.serve.load_server_config)(path)                        | Load a server config JSON of the form `{"name": str, "refs": [str, ...]}`.   |
|--------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| [`main`](#py2mcp.serve.main)([argv])                                    | CLI: `python -m py2mcp --config cfg.json` (or `--ref mod:func ...`).         |
| [`resolve_server_config`](#py2mcp.serve.resolve_server_config)(\*[, config, refs, name]) | Merge a config file and explicit `refs`/`name` into `(refs, name)`.          |
| [`serve_stdio`](#py2mcp.serve.serve_stdio)(refs, \*[, name, input_trans, ...]) | Build an MCP server from `'module:function'` refs and run it over stdio.     |

### py2mcp.serve.DFLT_SERVER_NAME *= 'py2mcp Server'*

Default server name when neither a config nor `--name` supplies one.

### py2mcp.serve.load_server_config(path)

Load a server config JSON of the form `{"name": str, "refs": [str, ...]}`.

Only the shape is checked here; the refs are resolved later, when the
server is built. An actionable error beats a server that starts with no
tools.

* **Parameters:**
  **path** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str) | [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)) – The JSON file to read.
* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)
* **Returns:**
  The parsed JSON object, untouched, with at least a `refs` list.
* **Raises:**
  * [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – The file is not valid JSON, or is not a JSON object carrying
        a `refs` list.
  * [**OSError**](https://docs.python.org/3/builtins/exceptions.html#OSError) – The file cannot be read.

### Examples

```pycon
>>> import json, tempfile
>>> from pathlib import Path
>>> path = Path(tempfile.mkdtemp()) / 'py2mcp_config.json'
>>> _ = path.write_text(json.dumps({'name': 'My Tools', 'refs': ['os.path:basename']}))
>>> load_server_config(path)
{'name': 'My Tools', 'refs': ['os.path:basename']}
>>> _ = path.write_text(json.dumps({'name': 'no refs here'}))
>>> load_server_config(path)
Traceback (most recent call last):
    ...
ValueError: py2mcp server config '...py2mcp_config.json' must be a JSON object with a "refs" list, ...
```

#### SEE ALSO
[`resolve_server_config()`](#py2mcp.serve.resolve_server_config): merge the config with command-line refs.

### py2mcp.serve.main(argv=None)

CLI: `python -m py2mcp --config cfg.json` (or `--ref mod:func ...`).

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### py2mcp.serve.resolve_server_config(, config=None, refs=(), name=None)

Merge a config file and explicit `refs`/`name` into `(refs, name)`.

Refs from `--ref` are appended after any from the config file; an explicit
`name` wins over the config’s. Pure (no I/O beyond reading `config`), so
it is unit-testable without standing up a server.

* **Parameters:**
  * **config** (`Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path), [`None`](https://docs.python.org/3/builtins/constants.html#None)]) – Path of a JSON config as read by [`load_server_config()`](#py2mcp.serve.load_server_config),
    or `None` for no config file.
  * **refs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Extra `'module:function'` references, appended after the
    config’s.
  * **name** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Server name; overrides the config’s `name`. When neither is
    given, `DFLT_SERVER_NAME`.
* **Return type:**
  [`tuple`](https://docs.python.org/3/builtins/stdtypes.html#tuple)[[`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)], [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]
* **Returns:**
  The merged list of references and the server name.
* **Raises:**
  [**ValueError**](https://docs.python.org/3/builtins/exceptions.html#ValueError) – Neither the config nor `refs` supplies any reference, or
      the config file is malformed (see [`load_server_config()`](#py2mcp.serve.load_server_config)).

### Examples

```pycon
>>> resolve_server_config(refs=['os.path:basename'], name='Paths')
(['os.path:basename'], 'Paths')
```

With a config file, its refs come first and its name is the fallback:

```pycon
>>> import json, tempfile
>>> from pathlib import Path
>>> path = Path(tempfile.mkdtemp()) / 'py2mcp_config.json'
>>> _ = path.write_text(json.dumps({'name': 'My Tools', 'refs': ['os.path:basename']}))
>>> resolve_server_config(config=path, refs=['os.path:dirname'])
(['os.path:basename', 'os.path:dirname'], 'My Tools')
>>> resolve_server_config(config=path, name='Override')
(['os.path:basename'], 'Override')
```

### py2mcp.serve.serve_stdio(refs, , name='py2mcp Server', input_trans=None, middleware=None, instructions=None)

Build an MCP server from `'module:function'` refs and run it over stdio.

Blocks, serving the MCP protocol on stdin/stdout until the host disconnects.
Thin wrapper over [`py2mcp.mk_mcp_from_refs()`](py2mcp.md#py2mcp.mk_mcp_from_refs) + `FastMCP.run` so that
packaged integrations have one command to launch. No example here: the call
does not return while the server runs.

* **Parameters:**
  * **refs** ([`Iterable`](https://docs.python.org/3/library/typing.html#typing.Iterable)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – `'module:function'` references, one per tool.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – Server name.
  * **input_trans** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]]) – Forwarded to [`py2mcp.mk_mcp_from_refs()`](py2mcp.md#py2mcp.mk_mcp_from_refs).
  * **middleware** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]) – A single FastMCP middleware or a list, forwarded for
    cross-cutting concerns; logging/metering is as useful on the local
    stdio path as on the remote one.
  * **instructions** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – The server’s model-facing description.

#### SEE ALSO
[`py2mcp.http.serve_http()`](py2mcp.http.md#py2mcp.http.serve_http): the same over Streamable HTTP.
[`main()`](#py2mcp.serve.main): the command line that calls this.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)
