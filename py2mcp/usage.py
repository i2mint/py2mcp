"""Per-call usage logging for a py2mcp / FastMCP server: who called which tool,
with what, and what came back.

A deployed connector otherwise leaves only a web-server access log (a timestamp
and a status code per ``POST /mcp``), which cannot even tell "a client connected"
from "a client used a tool". :class:`UsageLogger` is a FastMCP middleware that
writes **one record per tool call** (and, optionally, one per ``initialize``
handshake, flagged as such) to a *sink*: any callable taking a dict. It observes
only — a sink failure is logged and never fails the tool call — and it is off
unless a server attaches it (``middleware=[UsageLogger(...)]`` on any py2mcp
builder).

The record is a flat, JSON-ready dict::

    {"id": ..., "ts": "2026-10-02T14:03:11.123456+00:00", "event": "tool_call",
     "server": "snout", "version": "1.4.0", "session": ..., "request": ...,
     "caller": "someone@example.com", "tool": "search", "args": {"q": "..."},
     "outcome": "ok" | "empty" | "error" | "cancelled",
     "error_type": "ToolError", "error_cause": "ValueError", "error": "...",
     "result_chars": 812, "result_count": 7, "latency_ms": 41.2}

Field names map onto the OpenTelemetry MCP semantic conventions where those
exist (``tool`` ↔ ``gen_ai.tool.name``, ``args`` ↔ ``gen_ai.tool.call.arguments``,
``session`` ↔ ``mcp.session.id``, ``latency_ms`` ↔ ``mcp.server.operation.duration``,
``error_type`` ↔ ``error.type``); ``caller`` and ``outcome`` have no counterpart
there and are the two fields a connector owner actually asks about.

Three defaults need no new dependency:

- the **sink** is :class:`JsonlSink` — one JSON-lines file per day under
  ``$XDG_DATA_HOME/py2mcp/usage/<server>/`` (never inside the app directory or a
  repo), pruned to ``retention_days``; :func:`mapping_sink` adapts any
  ``MutableMapping`` (a ``dol`` store, hence blob storage) in one line. A sink
  may be ``async``; a sync sink runs on the event loop, so keep it local and
  cheap (a remote store belongs behind an async or batching sink);
- the **caller** is read from the verified OAuth token (:func:`token_caller`:
  ``email``, else ``sub``), ``None`` on an unauthenticated (stdio) path;
- the **outcome** is :func:`default_outcome`: ``error`` when the tool raised or
  flagged ``is_error``, ``empty`` when it returned nothing (the generic "no
  match"), else ``ok``. A custom classifier may return a mapping instead of a
  label (``{"outcome": "no_match", "result_count": 0}``) and it is merged into
  the record.

Privacy is a first-class setting, because the arguments are the users' own
questions: ``include_args=False`` drops them, ``redact=("api_key",)`` masks named
top-level fields, ``max_args_chars`` caps the rest — and because an exception
message or an ``is_error`` result often echoes the input (a validation error
quotes the offending value), **error text is recorded only when every argument
is**: with ``include_args=False`` or a non-empty ``redact``, a failure is
recorded as its ``error_type`` alone. Results are recorded as a size and a
count, never as content.

``session`` is the transport's ``mcp-session-id`` on HTTP (``None`` under
stateless HTTP, where there is none, and on the ``initialize`` request, which
precedes it), or FastMCP's per-session id on stdio. Reading it never creates
one. Reading the log back is :func:`iter_records` → :func:`summarize` →
:func:`format_summary`, also available as ``py2mcp usage <dir>``.

>>> from py2mcp import mk_mcp_server
>>> records = []
>>> def add(a: int, b: int) -> int:
...     return a + b
>>> mcp = mk_mcp_server(add, middleware=[UsageLogger(records.append, name='demo')])
>>> import asyncio
>>> _ = asyncio.run(mcp.call_tool('add', {'a': 2, 'b': 3}))
>>> records[0]['tool'], records[0]['args'], records[0]['outcome']
('add', {'a': 2, 'b': 3}, 'ok')
"""

from __future__ import annotations

import argparse
import asyncio
import inspect
import json
import logging
import os
import re
import threading
import time
import uuid
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import (
    Any,
    Callable,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Optional,
    Union,
)

from fastmcp.server.middleware import Middleware

__all__ = [
    "UsageLogger",
    "JsonlSink",
    "mapping_sink",
    "token_caller",
    "default_outcome",
    "default_usage_dir",
    "iter_records",
    "summarize",
    "format_summary",
    "main",
    "DFLT_RETENTION_DAYS",
    "DFLT_MAX_ARGS_CHARS",
    "DFLT_MAX_ERROR_CHARS",
    "REDACTED",
]

_logger = logging.getLogger(__name__)

#: Days of JSON-lines files :class:`JsonlSink` keeps before pruning. The arguments
#: are users' questions, so an unbounded log is a liability, not an asset.
DFLT_RETENTION_DAYS = 90

#: Cap on the serialized ``args`` stored per record (a pasted document as an
#: argument must not become a megabyte-per-call log).
DFLT_MAX_ARGS_CHARS = 4000

#: Cap on the error text stored per record (when error text is recorded at all).
DFLT_MAX_ERROR_CHARS = 500

#: What a redacted argument value is replaced with.
REDACTED = "<redacted>"

#: Server name used for the default sink directory when none is given.
DFLT_SERVER_SLUG = "server"

#: Outcome labels this module produces itself. A custom ``outcome`` callable may
#: return any label (e.g. ``"no_match"``, ``"refused"``); :func:`summarize` and
#: :func:`format_summary` tabulate whatever labels they see.
OUTCOME_OK, OUTCOME_EMPTY, OUTCOME_ERROR = "ok", "empty", "error"
OUTCOME_CANCELLED, OUTCOME_UNKNOWN = "cancelled", "unknown"

#: The HTTP header the Streamable-HTTP transport uses for its session id.
SESSION_HEADER = "mcp-session-id"

Sink = Callable[[dict], Any]
Caller = Callable[[], Optional[str]]
Outcome = Callable[[str, Any], Union[str, Mapping[str, Any]]]


# --- defaults for the three seams ---------------------------------------------


def token_caller() -> Optional[str]:
    """The caller's identity from the verified OAuth token, or ``None``.

    Reads FastMCP's current access token (set by the ``auth=`` resource-server
    layer on the HTTP path) and returns its ``email`` claim, else ``sub``,
    lowercased — the same rule ``enlace_metering.token_email`` applies, so one
    caller has one name across the platform. Deliberately **no** fallback to the
    OAuth ``client_id`` (a shared identity) and none to a guess: outside a
    request, or on an unauthenticated (stdio) server, the result is ``None`` and
    the record says ``"caller": null``.

    >>> token_caller() is None   # no request in flight here
    True
    """
    try:
        from fastmcp.server.dependencies import get_access_token

        token = get_access_token()
    except Exception:  # noqa: BLE001 — no active request/token context
        return None
    if token is None:
        return None
    claims = getattr(token, "claims", None) or {}
    ident = claims.get("email") or claims.get("sub")
    return str(ident).lower() if ident else None


def _is_empty_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def default_outcome(tool: str, result: Any) -> str:
    """Classify a tool result: ``error``, ``empty`` (the generic "no match"), or ``ok``.

    ``result`` is a FastMCP ``ToolResult`` (or anything with ``is_error``,
    ``content`` and ``structured_content``). A tool that *raised* never reaches
    this function — the middleware records ``error`` itself. ``empty`` is what a
    search returning no rows looks like from outside: no content blocks, or a
    structured ``{"result": []}`` / ``None`` / ``""`` / ``{}``. A tool with its
    own "no match" shape (``{"matches": [], "total": 0}``) is ``ok`` here; give
    the logger an ``outcome=`` that knows that shape.

    >>> class R:
    ...     def __init__(self, content=(), structured_content=None, is_error=False):
    ...         self.content, self.structured_content, self.is_error = list(content), structured_content, is_error
    >>> default_outcome('search', R(['x'], {'result': ['x']}))
    'ok'
    >>> default_outcome('search', R([], {'result': []}))
    'empty'
    >>> default_outcome('search', R(['oops'], is_error=True))
    'error'
    """
    if getattr(result, "is_error", False):
        return OUTCOME_ERROR
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        return OUTCOME_EMPTY if _is_empty_value(structured["result"]) else OUTCOME_OK
    content = getattr(result, "content", None)
    if not content and _is_empty_value(structured):
        return OUTCOME_EMPTY
    return OUTCOME_OK


def default_usage_dir(server: str = DFLT_SERVER_SLUG) -> Path:
    """Where :class:`JsonlSink` writes when given no root: the user data dir.

    ``$XDG_DATA_HOME/py2mcp/usage/<server>`` (``~/.local/share/...`` by default) —
    a package data directory, never the current directory, so a usage log is
    never one ``git add`` away from a repository.

    >>> str(default_usage_dir('snout')).endswith('py2mcp/usage/snout')
    True
    """
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return Path(base) / "py2mcp" / "usage" / _slug(server)


_SLUG_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _slug(name: Optional[str]) -> str:
    """A filesystem-safe slug for a server name (``'My Server' -> 'My_Server'``)."""
    s = _SLUG_RE.sub("_", (name or "").strip()).strip("._")
    return s or DFLT_SERVER_SLUG


# --- sinks ---------------------------------------------------------------------

_DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class JsonlSink:
    """Append records to one JSON-lines file per UTC day; prune old days.

    Files are ``<root>/<YYYY-MM-DD>.jsonl``. Files older than ``retention_days``
    (``0`` keeps today only, ``None`` keeps everything) are pruned at
    construction and on the first write of each new day. Each write is one
    ``O_APPEND`` write of one line, so concurrent workers on the same host
    interleave whole lines. ``root`` defaults to :func:`default_usage_dir`; it
    must be **one directory per server**, since the day files carry no server
    name and pruning covers the whole directory.

    The sink is built to be attached to a live server, so by default it does not
    raise: a directory that cannot be created at construction is reported via
    ``logging`` and retried on every write (``strict=True`` raises instead), and
    a directory removed at runtime is recreated on the next write.

    >>> import tempfile
    >>> sink = JsonlSink(tempfile.mkdtemp(), retention_days=None)
    >>> sink({'id': 'a', 'ts': '2026-10-02T10:00:00+00:00', 'event': 'tool_call'})
    >>> sorted(p.name for p in sink.root.iterdir())
    ['2026-10-02.jsonl']
    """

    def __init__(
        self,
        root: Optional[str | os.PathLike] = None,
        *,
        retention_days: Optional[int] = DFLT_RETENTION_DAYS,
        server: str = DFLT_SERVER_SLUG,
        strict: bool = False,
    ):
        self.root = Path(root) if root is not None else default_usage_dir(server)
        if retention_days is not None and retention_days < 0:
            raise ValueError(
                f"retention_days must be >= 0 or None, got {retention_days}"
            )
        self.retention_days = retention_days
        self._lock = threading.Lock()
        self._day: Optional[str] = None
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            self.prune()
        except OSError:
            if strict:
                raise
            _logger.error(
                "py2mcp.usage: cannot create usage-log dir %s; will retry on write",
                self.root,
                exc_info=True,
            )

    def __call__(self, record: dict) -> None:
        day = str(record.get("ts", ""))[:10]
        if not _DAY_RE.match(day):
            day = datetime.now(timezone.utc).date().isoformat()
        line = json.dumps(record, default=str, ensure_ascii=False) + "\n"
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            if day != self._day:
                self._day = day
                self.prune(today=date.fromisoformat(day))
            with open(self.root / f"{day}.jsonl", "a", encoding="utf-8") as f:
                f.write(line)

    def prune(self, *, today: Optional[date] = None) -> list[Path]:
        """Delete day files older than ``retention_days``; return what was removed."""
        if self.retention_days is None or not self.root.is_dir():
            return []
        today = today or datetime.now(timezone.utc).date()
        cutoff = today - timedelta(days=self.retention_days)
        removed = []
        for path in self.root.glob("*.jsonl"):
            if not _DAY_RE.match(path.stem):
                continue
            try:
                if date.fromisoformat(path.stem) < cutoff:
                    path.unlink()
                    removed.append(path)
            except ValueError:  # not a real date
                continue
            except OSError:
                _logger.warning("py2mcp.usage: could not prune %s", path, exc_info=True)
        return removed

    def __repr__(self) -> str:
        return f"JsonlSink({str(self.root)!r}, retention_days={self.retention_days})"


def _default_key(record: dict) -> str:
    return f"{str(record.get('ts', ''))[:10] or 'undated'}/{record['id']}.json"


def mapping_sink(
    store: MutableMapping, *, key: Callable[[dict], Any] = _default_key
) -> Sink:
    """A sink that does ``store[key(record)] = record`` — any ``MutableMapping``.

    The default key is ``"<YYYY-MM-DD>/<id>.json"``, so a ``dol`` file store lays
    records out one per file by day, and "last 30 days" is a key-prefix scan.
    The write happens on the event loop, so this is for a local store; a remote
    one (S3, a database) belongs behind an ``async`` sink or a batching one.

    >>> store = {}
    >>> sink = mapping_sink(store)
    >>> sink({'id': 'abc', 'ts': '2026-10-02T10:00:00+00:00'})
    >>> list(store)
    ['2026-10-02/abc.json']
    """

    def sink(record: dict) -> None:
        store[key(record)] = record

    return sink


# --- the middleware --------------------------------------------------------------


def _redact(args: dict, redact: Collection[str]) -> dict:
    return {k: (REDACTED if k in redact else v) for k, v in args.items()}


def _bounded_args(args: dict, max_chars: Optional[int]) -> tuple[Any, bool]:
    """Return ``(args_as_stored, truncated)``: the dict, or a cut string if too long."""
    if max_chars is None:
        return args, False
    text = json.dumps(args, default=str, ensure_ascii=False)
    if len(text) <= max_chars:
        return args, False
    return text[:max_chars] + "…", True


def _result_size(result: Any) -> tuple[int, Optional[int]]:
    """``(chars, count)``: text length of the content; the item count when it is a list."""
    chars = 0
    for block in getattr(result, "content", None) or ():
        chars += len(getattr(block, "text", "") or "")
    count: Optional[int] = None
    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict) and set(structured) == {"result"}:
        if isinstance(structured["result"], list):
            count = len(structured["result"])
    return chars, count


def _first_text(result: Any, limit: int) -> Optional[str]:
    for block in getattr(result, "content", None) or ():
        text = getattr(block, "text", None)
        if text:
            return str(text)[:limit]
    return None


def _session_id(fc: Any) -> Optional[str]:
    """The transport's session id, read without side effects (or ``None``).

    On HTTP it is the ``mcp-session-id`` header (absent under stateless HTTP and
    on the ``initialize`` request itself). Elsewhere (stdio, in-memory) it is
    FastMCP's per-session id, read only once a request context exists:
    ``Context.session_id`` *generates and caches* an id when read earlier, which
    would silently change the session id every tool sees.
    """
    try:
        from fastmcp.server.dependencies import get_http_request

        request = get_http_request()
    except Exception:  # noqa: BLE001 — no HTTP request in flight
        request = None
    if request is not None:
        return request.headers.get(SESSION_HEADER) or None
    if fc is not None and getattr(fc, "request_context", None) is not None:
        try:
            return str(fc.session_id)
        except Exception:  # noqa: BLE001
            return None
    return None


def _request_id(fc: Any) -> Optional[str]:
    if fc is None or getattr(fc, "request_context", None) is None:
        return None
    try:
        return str(fc.request_id)
    except Exception:  # noqa: BLE001
        return None


class UsageLogger(Middleware):
    """FastMCP middleware: one record per tool call (and per handshake) to ``sink``.

    Args:
        sink: ``record -> None`` (sync or ``async``). Default: a :class:`JsonlSink`
            under :func:`default_usage_dir` for ``name``. Any list's ``append``
            works for tests; :func:`mapping_sink` adapts a store.
        name: The connector/server name written into every record (and the
            default sink's directory).
        version: The connector version written into every record, if known.
        caller: ``() -> str | None`` resolving the caller for the in-flight
            request. Default :func:`token_caller`.
        outcome: ``(tool_name, result) -> label | mapping`` classifying a result
            that did not raise. Default :func:`default_outcome`. A mapping is
            merged into the record (it must carry ``"outcome"``), so a connector
            that knows its own "no match" shape can also set the true
            ``result_count``.
        include_args: Record the tool arguments at all. ``True`` by default —
            the arguments are the point of the log — but they are the users'
            questions, so a connector that must not keep them sets ``False``.
        redact: Top-level argument names whose values are replaced with
            :data:`REDACTED` (nested keys are not inspected; pre-shape the
            arguments with ``input_trans`` or drop them with ``include_args``).
        max_args_chars: Cap on the serialized arguments stored per record
            (``None`` for no cap).
        max_error_chars: Cap on the error text stored per record.
        handshakes: Also record ``initialize`` requests (as ``event:
            "initialize"`` with the client's name/version, and ``outcome``
            ``error`` if the handshake failed), so a connector that is *enabled*
            can be told from one that is *used*.

    Error text (an exception message, or an ``is_error`` result's text) is
    recorded only when ``include_args`` is true and ``redact`` is empty, because
    it routinely echoes the arguments; otherwise only ``error_type`` is kept.
    The logger never raises into the tool call: a failing sink, caller or
    classifier is reported via ``logging`` (logger ``py2mcp.usage``) and the
    call proceeds. A cancelled call is recorded as ``cancelled`` with no text;
    other ``BaseException``s (shutdown) pass through unrecorded.

    >>> records = []
    >>> logger = UsageLogger(records.append, name='demo', redact=('token',))
    >>> logger.name, logger.redact, logger.records_error_text
    ('demo', frozenset({'token'}), False)
    """

    def __init__(
        self,
        sink: Optional[Sink] = None,
        *,
        name: str = DFLT_SERVER_SLUG,
        version: Optional[str] = None,
        caller: Caller = token_caller,
        outcome: Outcome = default_outcome,
        include_args: bool = True,
        redact: Collection[str] = (),
        max_args_chars: Optional[int] = DFLT_MAX_ARGS_CHARS,
        max_error_chars: int = DFLT_MAX_ERROR_CHARS,
        handshakes: bool = True,
    ):
        self.sink: Sink = sink if sink is not None else JsonlSink(server=name)
        self._async_sink = inspect.iscoroutinefunction(self.sink)
        self.name = name
        self.version = version
        self.caller = caller
        self.outcome = outcome
        self.include_args = include_args
        self.redact = frozenset(redact)
        self.max_args_chars = max_args_chars
        self.max_error_chars = max_error_chars
        self.handshakes = handshakes

    @property
    def records_error_text(self) -> bool:
        """Whether error messages are stored (only when every argument is)."""
        return self.include_args and not self.redact

    # -- record assembly -------------------------------------------------------

    def _base_record(self, event: str, context: Any) -> dict:
        fc = getattr(context, "fastmcp_context", None)
        try:
            caller = self.caller()
        except Exception:  # noqa: BLE001 — identity must never break the call
            _logger.warning("py2mcp.usage: caller() raised", exc_info=True)
            caller = None
        return {
            "id": uuid.uuid4().hex,
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "server": self.name,
            "version": self.version,
            "session": _session_id(fc),
            "request": _request_id(fc),
            "caller": caller,
        }

    def _note_error(self, record: dict, exc: BaseException) -> None:
        record["outcome"] = OUTCOME_ERROR
        record["error_type"] = type(exc).__name__
        root = exc
        while root.__cause__ is not None:
            root = root.__cause__
        if root is not exc:  # FastMCP wraps a tool's exception in ToolError
            record["error_cause"] = type(root).__name__
        if self.records_error_text:
            record["error"] = str(exc)[: self.max_error_chars]

    def _note_result(self, record: dict, tool: str, result: Any) -> None:
        try:
            classified = self.outcome(tool, result)
        except Exception:  # noqa: BLE001 — a bad classifier must not break the call
            _logger.warning("py2mcp.usage: outcome() raised", exc_info=True)
            classified = OUTCOME_UNKNOWN
        try:
            record["result_chars"], record["result_count"] = _result_size(result)
            if getattr(result, "is_error", False):
                record["error_type"] = "ToolResult.is_error"
                if self.records_error_text:
                    record["error"] = _first_text(result, self.max_error_chars)
            if isinstance(classified, Mapping):
                record.update(classified)
                record["outcome"] = str(record.get("outcome") or OUTCOME_UNKNOWN)
            else:
                record["outcome"] = str(classified)
        except Exception:  # noqa: BLE001 — observe-only, whatever the result shape
            _logger.warning("py2mcp.usage: could not describe result", exc_info=True)
            record.setdefault("outcome", OUTCOME_UNKNOWN)

    async def _emit(self, record: dict) -> None:
        try:
            if self._async_sink:
                await self.sink(record)
            else:
                self.sink(record)
        except Exception:  # noqa: BLE001 — observe-only: never fail the call
            _logger.warning(
                "py2mcp.usage: sink failed for record %s",
                record.get("id"),
                exc_info=True,
            )

    # -- hooks -------------------------------------------------------------------

    async def on_initialize(self, context, call_next):
        if not self.handshakes:
            return await call_next(context)
        params = getattr(context.message, "params", None)
        client = getattr(params, "clientInfo", None)
        record = self._base_record("initialize", context)
        record.update(
            {
                "client": getattr(client, "name", None),
                "client_version": getattr(client, "version", None),
                "protocol": getattr(params, "protocolVersion", None),
            }
        )
        try:
            result = await call_next(context)
        except Exception as exc:
            self._note_error(record, exc)
            await self._emit(record)
            raise
        record["outcome"] = OUTCOME_OK
        await self._emit(record)
        return result

    async def on_call_tool(self, context, call_next):
        message = context.message
        tool = str(getattr(message, "name", None) or "unknown")
        record = self._base_record("tool_call", context)
        record["tool"] = tool
        if self.include_args:
            args = dict(getattr(message, "arguments", None) or {})
            stored, truncated = _bounded_args(
                _redact(args, self.redact), self.max_args_chars
            )
            record["args"] = stored
            if truncated:
                record["args_truncated"] = True
        t0 = time.perf_counter()
        try:
            result = await call_next(context)
        except asyncio.CancelledError:
            record["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            record["outcome"] = OUTCOME_CANCELLED
            await self._emit(record)
            raise
        except Exception as exc:
            record["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
            self._note_error(record, exc)
            await self._emit(record)
            raise
        record["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        self._note_result(record, tool, result)
        await self._emit(record)
        return result


# --- reading it back -------------------------------------------------------------


def _as_date(value: Optional[str | date | datetime]) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as exc:
        raise ValueError(f"expected a YYYY-MM-DD date, got {value!r}") from exc


def iter_records(
    root: str | os.PathLike,
    *,
    since: Optional[str | date | datetime] = None,
    until: Optional[str | date | datetime] = None,
) -> Iterator[dict]:
    """Yield the records under ``root`` (a :class:`JsonlSink` dir, or one ``.jsonl``).

    Day files are read in date order; ``since``/``until`` (inclusive, by day)
    select by file name, so a month out of a year of logs costs reading a month.
    Lines that are not valid JSON objects are skipped, not raised — a log is
    read long after it was written, and one torn line must not hide the rest.
    A ``root`` that does not exist raises ``FileNotFoundError`` rather than
    reading as an empty log.

    >>> import tempfile
    >>> sink = JsonlSink(tempfile.mkdtemp(), retention_days=None)
    >>> sink({'id': '1', 'ts': '2026-10-01T10:00:00+00:00', 'event': 'tool_call'})
    >>> sink({'id': '2', 'ts': '2026-10-02T10:00:00+00:00', 'event': 'tool_call'})
    >>> [r['id'] for r in iter_records(sink.root, since='2026-10-02')]
    ['2']
    """
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"no usage log at {root}")
    lo, hi = _as_date(since), _as_date(until)
    if root.is_file():
        files = [root]
    else:
        files = sorted(p for p in root.glob("*.jsonl") if _DAY_RE.match(p.stem))
    for path in files:
        if _DAY_RE.match(path.stem):
            day = date.fromisoformat(path.stem)
            if (lo and day < lo) or (hi and day > hi):
                continue
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if isinstance(record, dict):
                    yield record


def summarize(records: Iterable[dict]) -> dict:
    """Aggregate records into counts: by caller, by tool and outcome, by day.

    Returns a JSON-ready dict with ``calls``, ``handshakes``, ``first``/``last``
    timestamps, ``callers`` (calls per caller), ``servers`` (calls per server
    name, in case a directory holds more than one), ``tools`` (per tool:
    ``calls``, one count per outcome label seen, and mean/max latency), ``days``
    (calls per day) and ``outcomes`` (totals per label) — the "who used what,
    which tools fail, which questions return nothing" view.

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
    """
    calls = handshakes = 0
    first = last = None
    callers: Counter = Counter()
    servers: Counter = Counter()
    days: Counter = Counter()
    outcomes: Counter = Counter({OUTCOME_OK: 0, OUTCOME_EMPTY: 0, OUTCOME_ERROR: 0})
    tools: dict[str, dict] = defaultdict(
        lambda: {"calls": 0, "_sum": 0.0, "_max": 0.0, "_labels": Counter()}
    )
    for r in records:
        ts = r.get("ts")
        if ts:
            first = ts if first is None or ts < first else first
            last = ts if last is None or ts > last else last
        if r.get("event") == "initialize":
            handshakes += 1
            continue
        if r.get("event", "tool_call") != "tool_call":
            continue
        calls += 1
        callers[r.get("caller") or "(anonymous)"] += 1
        servers[r.get("server") or "(unnamed)"] += 1
        days[str(ts or "")[:10] or "undated"] += 1
        label = str(r.get("outcome") or OUTCOME_UNKNOWN)
        outcomes[label] += 1
        t = tools[str(r.get("tool") or "unknown")]
        t["calls"] += 1
        t["_labels"][label] += 1
        latency = r.get("latency_ms")
        if isinstance(latency, (int, float)):
            t["_sum"] += float(latency)
            t["_max"] = max(t["_max"], float(latency))
    labels = list(outcomes)
    tools_out = {}
    for name, t in sorted(tools.items(), key=lambda kv: -kv[1]["calls"]):
        n = t["calls"]
        tools_out[name] = {"calls": n}
        for label in labels:
            tools_out[name][label] = t["_labels"].get(label, 0)
        tools_out[name]["latency_ms_mean"] = round(t["_sum"] / n, 1) if n else 0.0
        tools_out[name]["latency_ms_max"] = round(t["_max"], 1)
    return {
        "calls": calls,
        "handshakes": handshakes,
        "first": first,
        "last": last,
        "callers": dict(callers.most_common()),
        "servers": dict(servers.most_common()),
        "tools": tools_out,
        "days": dict(sorted(days.items())),
        "outcomes": dict(outcomes),
    }


def format_summary(summary: dict) -> str:
    """Render :func:`summarize` output as plain text, one column per outcome label.

    >>> print(format_summary(summarize([
    ...     {'event': 'tool_call', 'ts': '2026-10-02T08:01:00+00:00', 'caller': 'a',
    ...      'tool': 'search', 'outcome': 'ok', 'latency_ms': 10.0}])))
    calls: 1   handshakes: 0   first: 2026-10-02T08:01:00+00:00   last: 2026-10-02T08:01:00+00:00
    outcomes: ok=1 empty=0 error=0
    <BLANKLINE>
    callers
      a                                   1
    <BLANKLINE>
    tools                      calls     ok  empty  error  mean_ms   max_ms
      search                       1      1      0      0     10.0     10.0
    <BLANKLINE>
    days
      2026-10-02                          1
    """
    labels = list(summary["outcomes"])
    lines = [
        f"calls: {summary['calls']}   handshakes: {summary['handshakes']}   "
        f"first: {summary.get('first')}   last: {summary.get('last')}",
        "outcomes: " + " ".join(f"{k}={v}" for k, v in summary["outcomes"].items()),
        "",
        "callers",
    ]
    lines += [f"  {c:<34}{n:>5}" for c, n in summary["callers"].items()]
    if len(summary.get("servers", {})) > 1:
        lines += ["", "servers"]
        lines += [f"  {s:<34}{n:>5}" for s, n in summary["servers"].items()]
    width = max(7, *(len(label) + 2 for label in labels))
    header = f"{'tools':<24}{'calls':>8}" + "".join(
        f"{label:>{width}}" for label in labels
    )
    lines += ["", header + f"{'mean_ms':>9}{'max_ms':>9}"]
    for name, t in summary["tools"].items():
        row = f"  {name:<22}{t['calls']:>8}"
        row += "".join(f"{t.get(label, 0):>{width}}" for label in labels)
        lines.append(row + f"{t['latency_ms_mean']:>9.1f}{t['latency_ms_max']:>9.1f}")
    lines += ["", "days"]
    lines += [f"  {d:<34}{n:>5}" for d, n in summary["days"].items()]
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> None:
    """CLI: ``py2mcp usage <dir> [--since D] [--until D] [--json] [--records]``."""
    parser = argparse.ArgumentParser(
        prog="py2mcp usage",
        description="Summarize a py2mcp usage log (a JsonlSink directory or file).",
    )
    parser.add_argument("root", help="The usage-log directory (or one .jsonl file).")
    parser.add_argument("--since", help="First day to include (YYYY-MM-DD).")
    parser.add_argument("--until", help="Last day to include (YYYY-MM-DD).")
    parser.add_argument(
        "--json", action="store_true", help="Print the summary as JSON instead of text."
    )
    parser.add_argument(
        "--records",
        action="store_true",
        help="Print the selected records (one JSON object per line) instead of a summary.",
    )
    args = parser.parse_args(argv)
    try:
        records = list(iter_records(args.root, since=args.since, until=args.until))
    except (FileNotFoundError, ValueError) as exc:
        parser.error(str(exc))
    if args.records:
        for record in records:
            print(json.dumps(record, ensure_ascii=False))
        return
    summary = summarize(records)
    print(json.dumps(summary, indent=2) if args.json else format_summary(summary))


if __name__ == "__main__":
    main()
