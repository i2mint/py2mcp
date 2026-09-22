# py2mcp

Quick MCP (Model Context Protocol) server creation from Python functions: pass
ordinary functions in, get a `FastMCP` server out, with each function registered
as a tool. Builders return a server *object* and leave running it to the caller.

## Module map (`py2mcp/`)

- `main.py` — the builders: `mk_mcp_server` (functions -> server), `mk_mcp_from_refs`
  (`'module:function'` strings -> server), `mk_mcp_from_store` (list/get/set/delete
  tools over any `MutableMapping`).
- `base.py` — private helpers shared by the builders: argument normalization
  (`funcs`/`middleware` accept one object or an iterable) and the
  `input_trans`-applying wrapper.
- `trans.py` — `mk_input_trans`: per-argument conversion of tool inputs (MCP
  clients send JSON; a tool wanting a `numpy` array/`Path`/parsed date needs
  conversion first).
- `serve.py` — `serve_stdio` + config resolution: the packaged stdio launcher.
- `http.py` — `serve_http`, `mk_http_app`, `mk_auth_provider`: the *remote*
  counterpart to `serve.py` — Streamable HTTP with optional OAuth 2.1, for a
  server reached over public HTTPS (e.g. a claude.ai custom connector).
- `util.py` — `import_object` (resolve `'module:function'` strings) and
  turning a mapping into CRUD functions — usable standalone.
- `__main__.py` — CLI entry point.

## Tests & lint (verified)

```bash
uv venv .venv && uv pip install -e . pytest ruff
.venv/bin/pytest -v --tb=short   # 63 passed — collects only tests/ (see gotcha)
.venv/bin/ruff check .
```
Or `wads ci-local` for the matrix (Python 3.10 + 3.12, Windows included).

**Gotcha:** `[tool.pytest.ini_options].testpaths = ["tests"]` means
`py2mcp/tests/test_basic.py` is **not** collected by a bare `pytest` run (or by
CI) — it passes (20 tests) when run explicitly
(`pytest py2mcp/tests/test_basic.py`) but is otherwise dead weight/blind spot.
Worth consolidating into `tests/` or adding to `testpaths`.

**CI note:** `.github/workflows/ci.yml` is currently an inline uv workflow, not
yet the i2mint/wads reusable-workflow stub — [i2mint/py2mcp#15](https://github.com/i2mint/py2mcp/pull/15)
(open) attempts that migration but hits an unresolved `action_required`/zero-jobs
hosted-CI anomaly on first use of the reusable workflow in this repo; tracked in
[i2mint/py2mcp#16](https://github.com/i2mint/py2mcp/issues/16). Until that lands,
CI here runs the inline workflow normally.

## Dependents

`enlace-connector` imports this package — check its tests before changing any
`mk_mcp_*` builder's signature or the shape of the server it returns.
