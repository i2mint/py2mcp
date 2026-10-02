# py2mcp.usage

Per-call usage logging for a py2mcp / FastMCP server: who called which tool,
with what, and what came back.

A deployed connector otherwise leaves only a web-server access log (a timestamp
and a status code per `POST /mcp`), which cannot even tell “a client connected”
from “a client used a tool”. [`UsageLogger`](#py2mcp.usage.UsageLogger) is a FastMCP middleware that
writes **one record per tool call** (and, optionally, one per `initialize`
handshake, flagged as such) to a *sink*: any callable taking a dict. It observes
only — a sink failure is logged and never fails the tool call — and it is off
unless a server attaches it (`middleware=[UsageLogger(...)]` on any py2mcp
builder).

The record is a flat, JSON-ready dict:

```default
{"id": ..., "ts": "2026-10-02T14:03:11.123456+00:00", "event": "tool_call",
 "server": "snout", "version": "1.4.0", "session": ..., "request": ...,
 "caller": "someone@example.com", "tool": "search", "args": {"q": "..."},
 "outcome": "ok" | "empty" | "error" | "cancelled",
 "error_type": "ToolError", "error_cause": "ValueError", "error": "...",
 "result_chars": 812, "result_count": 7, "latency_ms": 41.2}
```

Field names map onto the OpenTelemetry MCP semantic conventions where those
exist (`tool` ↔ `gen_ai.tool.name`, `args` ↔ `gen_ai.tool.call.arguments`,
`session` ↔ `mcp.session.id`, `latency_ms` ↔ `mcp.server.operation.duration`,
`error_type` ↔ `error.type`); `caller` and `outcome` have no counterpart
there and are the two fields a connector owner actually asks about.

Three defaults need no new dependency:

- the **sink** is [`JsonlSink`](#py2mcp.usage.JsonlSink) — one JSON-lines file per day under
  `$XDG_DATA_HOME/py2mcp/usage/<server>/` (never inside the app directory or a
  repo), pruned to `retention_days`; [`mapping_sink()`](#py2mcp.usage.mapping_sink) adapts any
  `MutableMapping` (a `dol` store, hence blob storage) in one line. A sink
  may be `async`; a sync sink runs on the event loop, so keep it local and
  cheap (a remote store belongs behind an async or batching sink);
- the **caller** is read from the verified OAuth token ([`token_caller()`](#py2mcp.usage.token_caller):
  `email`, else `sub`), `None` on an unauthenticated (stdio) path;
- the **outcome** is [`default_outcome()`](#py2mcp.usage.default_outcome): `error` when the tool raised or
  flagged `is_error`, `empty` when it returned nothing (the generic “no
  match”), else `ok`. A custom classifier may return a mapping instead of a
  label (`{"outcome": "no_match", "result_count": 0}`) and it is merged into
  the record.

Privacy is a first-class setting, because the arguments are the users’ own
questions: `include_args=False` drops them, `redact=("api_key",)` masks named
top-level fields, `max_args_chars` caps the rest — and because an exception
message or an `is_error` result often echoes the input (a validation error
quotes the offending value), \*\*error text is recorded only when every argument
is\*\*: with `include_args=False` or a non-empty `redact`, a failure is
recorded as its `error_type` alone. Results are recorded as a size and a
count, never as content.

`session` is the transport’s `mcp-session-id` on HTTP (`None` under
stateless HTTP, where there is none, and on the `initialize` request, which
precedes it), or FastMCP’s per-session id on stdio. Reading it never creates
one. Reading the log back is [`iter_records()`](#py2mcp.usage.iter_records) → [`summarize()`](#py2mcp.usage.summarize) →
[`format_summary()`](#py2mcp.usage.format_summary), also available as `py2mcp usage <dir>`.

```pycon
>>> from py2mcp import mk_mcp_server
>>> records = []
>>> def add(a: int, b: int) -> int:
...     return a + b
>>> mcp = mk_mcp_server(add, middleware=[UsageLogger(records.append, name='demo')])
>>> import asyncio
>>> _ = asyncio.run(mcp.call_tool('add', {'a': 2, 'b': 3}))
>>> records[0]['tool'], records[0]['args'], records[0]['outcome']
('add', {'a': 2, 'b': 3}, 'ok')
```

### Module Attributes

| [`DFLT_RETENTION_DAYS`](#py2mcp.usage.DFLT_RETENTION_DAYS)   | Days of JSON-lines files [`JsonlSink`](#py2mcp.usage.JsonlSink) keeps before pruning.                  |
|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| [`DFLT_MAX_ARGS_CHARS`](#py2mcp.usage.DFLT_MAX_ARGS_CHARS)   | Cap on the serialized `args` stored per record (a pasted document as an argument must not become a megabyte-per-call log). |
| [`DFLT_MAX_ERROR_CHARS`](#py2mcp.usage.DFLT_MAX_ERROR_CHARS)  | Cap on the error text stored per record (when error text is recorded at all).                                              |
| [`REDACTED`](#py2mcp.usage.REDACTED)              | What a redacted argument value is replaced with.                                                                           |

### Functions

| [`mapping_sink`](#py2mcp.usage.mapping_sink)(store, \*[, key])         | A sink that does `store[key(record)] = record` — any `MutableMapping`.                                                  |
|-----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| [`token_caller`](#py2mcp.usage.token_caller)()                         | The caller's identity from the verified OAuth token, or `None`.                                                         |
| [`default_outcome`](#py2mcp.usage.default_outcome)(tool, result)          | Classify a tool result: `error`, `empty` (the generic "no match"), or `ok`.                                             |
| [`default_usage_dir`](#py2mcp.usage.default_usage_dir)([server])            | Where [`JsonlSink`](#py2mcp.usage.JsonlSink) writes when given no root: the user data dir.          |
| [`iter_records`](#py2mcp.usage.iter_records)(root, \*[, since, until]) | Yield the records under `root` (a [`JsonlSink`](#py2mcp.usage.JsonlSink) dir, or one `.jsonl`).     |
| [`summarize`](#py2mcp.usage.summarize)(records)                     | Aggregate records into counts: by caller, by tool and outcome, by day.                                                  |
| [`format_summary`](#py2mcp.usage.format_summary)(summary)                | Render [`summarize()`](#py2mcp.usage.summarize) output as plain text, one column per outcome label. |
| [`main`](#py2mcp.usage.main)([argv])                           | CLI: `py2mcp usage <dir> [--since D] [--until D] [--json] [--records]`.                                                 |

### Classes

| [`UsageLogger`](#py2mcp.usage.UsageLogger)([sink, name, version, caller, ...])   | FastMCP middleware: one record per tool call (and per handshake) to `sink`.   |
|----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| [`JsonlSink`](#py2mcp.usage.JsonlSink)([root, retention_days, server, strict]) | Append records to one JSON-lines file per UTC day; prune old days.            |

### py2mcp.usage.DFLT_MAX_ARGS_CHARS *= 4000*

Cap on the serialized `args` stored per record (a pasted document as an
argument must not become a megabyte-per-call log).

### py2mcp.usage.DFLT_MAX_ERROR_CHARS *= 500*

Cap on the error text stored per record (when error text is recorded at all).

### py2mcp.usage.DFLT_RETENTION_DAYS *= 90*

Days of JSON-lines files [`JsonlSink`](#py2mcp.usage.JsonlSink) keeps before pruning. The arguments
are users’ questions, so an unbounded log is a liability, not an asset.

### *class* py2mcp.usage.JsonlSink(root=None, , retention_days=90, server='server', strict=False)

Bases: [`object`](https://docs.python.org/3/builtins/functions.html#object)

Append records to one JSON-lines file per UTC day; prune old days.

Files are `<root>/<YYYY-MM-DD>.jsonl`. Files older than `retention_days`
(`0` keeps today only, `None` keeps everything) are pruned at
construction and on the first write of each new day. Each write is one
`O_APPEND` write of one line, so concurrent workers on the same host
interleave whole lines. `root` defaults to [`default_usage_dir()`](#py2mcp.usage.default_usage_dir); it
must be **one directory per server**, since the day files carry no server
name and pruning covers the whole directory.

The sink is built to be attached to a live server, so by default it does not
raise: a directory that cannot be created at construction is reported via
`logging` and retried on every write (`strict=True` raises instead), and
a directory removed at runtime is recreated on the next write.

```pycon
>>> import tempfile
>>> sink = JsonlSink(tempfile.mkdtemp(), retention_days=None)
>>> sink({'id': 'a', 'ts': '2026-10-02T10:00:00+00:00', 'event': 'tool_call'})
>>> sorted(p.name for p in sink.root.iterdir())
['2026-10-02.jsonl']
```

#### prune(, today=None)

Delete day files older than `retention_days`; return what was removed.

* **Return type:**
  [`list`](https://docs.python.org/3/builtins/stdtypes.html#list)[[`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)]

### py2mcp.usage.REDACTED *= '<redacted>'*

What a redacted argument value is replaced with.

### *class* py2mcp.usage.UsageLogger(sink=None, \*, name='server', version=None, caller=<function token_caller>, outcome=<function default_outcome>, include_args=True, redact=(), max_args_chars=4000, max_error_chars=500, handshakes=True)

Bases: `Middleware`

FastMCP middleware: one record per tool call (and per handshake) to `sink`.

* **Parameters:**
  * **sink** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]) – `record -> None` (sync or `async`). Default: a [`JsonlSink`](#py2mcp.usage.JsonlSink)
    under [`default_usage_dir()`](#py2mcp.usage.default_usage_dir) for `name`. Any list’s `append`
    works for tests; [`mapping_sink()`](#py2mcp.usage.mapping_sink) adapts a store.
  * **name** ([`str`](https://docs.python.org/3/builtins/stdtypes.html#str)) – The connector/server name written into every record (and the
    default sink’s directory).
  * **version** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – The connector version written into every record, if known.
  * **caller** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[], [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]]) – `() -> str | None` resolving the caller for the in-flight
    request. Default [`token_caller()`](#py2mcp.usage.token_caller).
  * **outcome** ([`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)], `Union`[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Mapping`](https://docs.python.org/3/library/typing.html#typing.Mapping)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str), [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]]]) – `(tool_name, result) -> label | mapping` classifying a result
    that did not raise. Default [`default_outcome()`](#py2mcp.usage.default_outcome). A mapping is
    merged into the record (it must carry `"outcome"`), so a connector
    that knows its own “no match” shape can also set the true
    `result_count`.
  * **include_args** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Record the tool arguments at all. `True` by default —
    the arguments are the point of the log — but they are the users’
    questions, so a connector that must not keep them sets `False`.
  * **redact** ([`Collection`](https://docs.python.org/3/library/typing.html#typing.Collection)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]) – Top-level argument names whose values are replaced with
    [`REDACTED`](#py2mcp.usage.REDACTED) (nested keys are not inspected; pre-shape the
    arguments with `input_trans` or drop them with `include_args`).
  * **max_args_chars** ([`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`int`](https://docs.python.org/3/builtins/functions.html#int)]) – Cap on the serialized arguments stored per record
    (`None` for no cap).
  * **max_error_chars** ([`int`](https://docs.python.org/3/builtins/functions.html#int)) – Cap on the error text stored per record.
  * **handshakes** ([`bool`](https://docs.python.org/3/builtins/functions.html#bool)) – Also record `initialize` requests (as `event:
    "initialize"` with the client’s name/version, and `outcome`
    `error` if the handshake failed), so a connector that is *enabled*
    can be told from one that is *used*.

Error text (an exception message, or an `is_error` result’s text) is
recorded only when `include_args` is true and `redact` is empty, because
it routinely echoes the arguments; otherwise only `error_type` is kept.
The logger never raises into the tool call: a failing sink, caller or
classifier is reported via `logging` (logger `py2mcp.usage`) and the
call proceeds. A cancelled call is recorded as `cancelled` with no text;
other 

```
``
```

BaseException\`\`s (shutdown) pass through unrecorded.

```pycon
>>> records = []
>>> logger = UsageLogger(records.append, name='demo', redact=('token',))
>>> logger.name, logger.redact, logger.records_error_text
('demo', frozenset({'token'}), False)
```

#### *property* records_error_text *: [bool](https://docs.python.org/3/builtins/functions.html#bool)*

Whether error messages are stored (only when every argument is).

### py2mcp.usage.default_outcome(tool, result)

Classify a tool result: `error`, `empty` (the generic “no match”), or `ok`.

`result` is a FastMCP `ToolResult` (or anything with `is_error`,
`content` and `structured_content`). A tool that *raised* never reaches
this function — the middleware records `error` itself. `empty` is what a
search returning no rows looks like from outside: no content blocks, or a
structured `{"result": []}` / `None` / `""` / `{}`. A tool with its
own “no match” shape (`{"matches": [], "total": 0}`) is `ok` here; give
the logger an `outcome=` that knows that shape.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> class R:
...     def __init__(self, content=(), structured_content=None, is_error=False):
...         self.content, self.structured_content, self.is_error = list(content), structured_content, is_error
>>> default_outcome('search', R(['x'], {'result': ['x']}))
'ok'
>>> default_outcome('search', R([], {'result': []}))
'empty'
>>> default_outcome('search', R(['oops'], is_error=True))
'error'
```

### py2mcp.usage.default_usage_dir(server='server')

Where [`JsonlSink`](#py2mcp.usage.JsonlSink) writes when given no root: the user data dir.

`$XDG_DATA_HOME/py2mcp/usage/<server>` (`~/.local/share/...` by default) —
a package data directory, never the current directory, so a usage log is
never one `git add` away from a repository.

* **Return type:**
  [`Path`](https://docs.python.org/3/library/pathlib.html#pathlib.Path)

```pycon
>>> str(default_usage_dir('snout')).endswith('py2mcp/usage/snout')
True
```

### py2mcp.usage.format_summary(summary)

Render [`summarize()`](#py2mcp.usage.summarize) output as plain text, one column per outcome label.

* **Return type:**
  [`str`](https://docs.python.org/3/builtins/stdtypes.html#str)

```pycon
>>> print(format_summary(summarize([
...     {'event': 'tool_call', 'ts': '2026-10-02T08:01:00+00:00', 'caller': 'a',
...      'tool': 'search', 'outcome': 'ok', 'latency_ms': 10.0}])))
calls: 1   handshakes: 0   first: 2026-10-02T08:01:00+00:00   last: 2026-10-02T08:01:00+00:00
outcomes: ok=1 empty=0 error=0

callers
  a                                   1

tools                      calls     ok  empty  error  mean_ms   max_ms
  search                       1      1      0      0     10.0     10.0

days
  2026-10-02                          1
```

### py2mcp.usage.iter_records(root, , since=None, until=None)

Yield the records under `root` (a [`JsonlSink`](#py2mcp.usage.JsonlSink) dir, or one `.jsonl`).

Day files are read in date order; `since`/`until` (inclusive, by day)
select by file name, so a month out of a year of logs costs reading a month.
Lines that are not valid JSON objects are skipped, not raised — a log is
read long after it was written, and one torn line must not hide the rest.
A `root` that does not exist raises `FileNotFoundError` rather than
reading as an empty log.

* **Return type:**
  [`Iterator`](https://docs.python.org/3/library/typing.html#typing.Iterator)[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)]

```pycon
>>> import tempfile
>>> sink = JsonlSink(tempfile.mkdtemp(), retention_days=None)
>>> sink({'id': '1', 'ts': '2026-10-01T10:00:00+00:00', 'event': 'tool_call'})
>>> sink({'id': '2', 'ts': '2026-10-02T10:00:00+00:00', 'event': 'tool_call'})
>>> [r['id'] for r in iter_records(sink.root, since='2026-10-02')]
['2']
```

### py2mcp.usage.main(argv=None)

CLI: `py2mcp usage <dir> [--since D] [--until D] [--json] [--records]`.

* **Return type:**
  [`None`](https://docs.python.org/3/builtins/constants.html#None)

### py2mcp.usage.mapping_sink(store, \*, key=<function \_default_key>)

A sink that does `store[key(record)] = record` — any `MutableMapping`.

The default key is `"<YYYY-MM-DD>/<id>.json"`, so a `dol` file store lays
records out one per file by day, and “last 30 days” is a key-prefix scan.
The write happens on the event loop, so this is for a local store; a remote
one (S3, a database) belongs behind an `async` sink or a batching one.

* **Return type:**
  [`Callable`](https://docs.python.org/3/library/typing.html#typing.Callable)[[[`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)], [`Any`](https://docs.python.org/3/library/typing.html#typing.Any)]

```pycon
>>> store = {}
>>> sink = mapping_sink(store)
>>> sink({'id': 'abc', 'ts': '2026-10-02T10:00:00+00:00'})
>>> list(store)
['2026-10-02/abc.json']
```

### py2mcp.usage.summarize(records)

Aggregate records into counts: by caller, by tool and outcome, by day.

Returns a JSON-ready dict with `calls`, `handshakes`, `first`/`last`
timestamps, `callers` (calls per caller), `servers` (calls per server
name, in case a directory holds more than one), `tools` (per tool:
`calls`, one count per outcome label seen, and mean/max latency), `days`
(calls per day) and `outcomes` (totals per label) — the “who used what,
which tools fail, which questions return nothing” view.

* **Return type:**
  [`dict`](https://docs.python.org/3/builtins/stdtypes.html#dict)

```pycon
>>> recs = [
...     {'event': 'initialize', 'ts': '2026-10-02T08:00:00+00:00', 'caller': 'a'},
...     {'event': 'tool_call', 'ts': '2026-10-02T08:01:00+00:00', 'caller': 'a',
...      'tool': 'search', 'outcome': 'ok', 'latency_ms': 10.0},
...     {'event': 'tool_call', 'ts': '2026-10-02T09:00:00+00:00', 'caller': 'b',
...      'tool': 'search', 'outcome': 'no_match', 'latency_ms': 30.0},
... ]
>>> s = summarize(recs)
>>> s['calls'], s['handshakes'], s['callers'], s['outcomes']
(2, 1, {'a': 1, 'b': 1}, {'ok': 1, 'empty': 0, 'error': 0, 'no_match': 1})
>>> s['tools']['search']['latency_ms_mean'], s['tools']['search']['latency_ms_max']
(20.0, 30.0)
```

### py2mcp.usage.token_caller()

The caller’s identity from the verified OAuth token, or `None`.

Reads FastMCP’s current access token (set by the `auth=` resource-server
layer on the HTTP path) and returns its `email` claim, else `sub`,
lowercased — the same rule `enlace_metering.token_email` applies, so one
caller has one name across the platform. Deliberately **no** fallback to the
OAuth `client_id` (a shared identity) and none to a guess: outside a
request, or on an unauthenticated (stdio) server, the result is `None` and
the record says `"caller": null`.

* **Return type:**
  [`Optional`](https://docs.python.org/3/library/typing.html#typing.Optional)[[`str`](https://docs.python.org/3/builtins/stdtypes.html#str)]

```pycon
>>> token_caller() is None   # no request in flight here
True
```
