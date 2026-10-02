"""Tests for ``py2mcp.usage`` — the per-call usage logger, its sinks and reader.

These drive a real FastMCP server through the in-memory ``Client`` so the records
come from the actual middleware path (initialize, tools/call, raised errors,
``is_error`` results), and exercise the JSON-lines sink's day files, pruning and
read-back, plus the ``py2mcp usage`` CLI. See i2mint/py2mcp#20.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, timedelta

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError
from fastmcp.tools.base import ToolResult

from py2mcp import mk_mcp_server, mk_http_app
from py2mcp.serve import main as cli_main
from py2mcp.usage import (
    DFLT_RETENTION_DAYS,
    REDACTED,
    JsonlSink,
    UsageLogger,
    default_outcome,
    default_usage_dir,
    format_summary,
    iter_records,
    mapping_sink,
    summarize,
    token_caller,
)


# --- tools under test ------------------------------------------------------------


def search(q: str, api_key: str = "") -> list[str]:
    """Return matches (none for 'none')."""
    return [] if q == "none" else [q, q.upper()]


def boom(x: int) -> int:
    """Always fails."""
    raise ValueError("bad input")


def soft_fail(x: int) -> ToolResult:
    """Fails the MCP way: an is_error result, not an exception."""
    return ToolResult(content="nope", is_error=True)


def _run(server, calls):
    async def go():
        out = []
        async with Client(server) as client:
            for name, args in calls:
                try:
                    out.append(await client.call_tool(name, args))
                except ToolError as e:
                    out.append(e)
        return out

    return asyncio.run(go())


def _server(records, **kw):
    logger = UsageLogger(records.append, name="t", version="1.0", **kw)
    return mk_mcp_server([search, boom, soft_fail], middleware=[logger])


# --- the middleware ------------------------------------------------------------


def test_records_ok_empty_and_raised_error():
    records = []
    server = _server(records)
    _run(
        server, [("search", {"q": "x"}), ("search", {"q": "none"}), ("boom", {"x": 1})]
    )
    calls = [r for r in records if r["event"] == "tool_call"]
    assert [r["tool"] for r in calls] == ["search", "search", "boom"]
    assert [r["outcome"] for r in calls] == ["ok", "empty", "error"]
    ok, empty, err = calls
    assert ok["args"] == {"q": "x"}
    assert ok["result_count"] == 2 and ok["result_chars"] > 0
    assert empty["result_count"] == 0
    assert (
        err["error"].startswith("ValueError: bad input") or "bad input" in err["error"]
    )
    for r in calls:
        assert r["server"] == "t" and r["version"] == "1.0"
        assert isinstance(r["latency_ms"], float) and r["latency_ms"] >= 0
        assert r["ts"].endswith("+00:00")
        assert r["caller"] is None  # no OAuth token on the in-memory path
        assert r["session"] and r["request"]
        assert "error_type" not in r or r["outcome"] == "error"
        assert len(r["id"]) == 32


def test_is_error_result_is_an_error_outcome():
    records = []
    _run(_server(records), [("soft_fail", {"x": 1})])
    (r,) = [r for r in records if r["event"] == "tool_call"]
    assert r["outcome"] == "error"
    assert r["error_type"] == "ToolResult.is_error" and r["error"] == "nope"


def test_handshake_is_recorded_and_flagged():
    records = []
    _run(_server(records), [("search", {"q": "x"})])
    init = [r for r in records if r["event"] == "initialize"]
    assert len(init) == 1
    assert init[0]["client"]  # the fastmcp client's name
    assert init[0]["protocol"]
    assert init[0]["outcome"] == "ok"
    assert "tool" not in init[0]


def test_error_text_is_dropped_when_args_are_not_fully_recorded():
    # A validation error / a tool's own message echoes the input; with
    # include_args=False or any redaction only the exception type survives.
    for kw in ({"include_args": False}, {"redact": ("q",)}):
        records = []
        _run(
            _server(records, **kw),
            [
                ("boom", {"x": 1}),
                ("soft_fail", {"x": 1}),
                ("search", {"q": "not-an-int-for-x", "api_key": "k"}),
            ],
        )
        calls = [r for r in records if r["event"] == "tool_call"]
        assert calls[0]["error_cause"] == "ValueError" and "error" not in calls[0]
        assert (
            calls[1]["error_type"] == "ToolResult.is_error" and "error" not in calls[1]
        )
        assert "not-an-int" not in json.dumps(records)


def test_validation_error_text_is_capped_and_typed():
    records = []
    _run(_server(records, max_error_chars=10), [("boom", {"x": "zzz"})])  # x: int
    (r,) = [r for r in records if r["event"] == "tool_call"]
    assert r["outcome"] == "error" and r["error_type"]
    assert len(r["error"]) <= 10


def test_cancellation_is_not_an_error():
    records = []

    async def slow(x: int) -> int:
        await asyncio.sleep(10)
        return x

    server = mk_mcp_server([slow], middleware=[UsageLogger(records.append, name="t")])

    async def go():
        async with Client(server) as client:
            task = asyncio.ensure_future(client.call_tool("slow", {"x": 1}))
            await asyncio.sleep(0.05)
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, ToolError):
                pass

    asyncio.run(go())
    calls = [r for r in records if r["event"] == "tool_call"]
    assert calls and calls[0]["outcome"] == "cancelled" and "error" not in calls[0]


def test_outcome_may_return_a_mapping():
    records = []

    def classify(tool, result):
        n = len(result.structured_content["result"])
        return {"outcome": "no_match" if n == 0 else "hit", "result_count": n * 100}

    _run(
        _server(records, outcome=classify),
        [("search", {"q": "none"}), ("search", {"q": "x"})],
    )
    calls = [r for r in records if r["event"] == "tool_call"]
    assert [(r["outcome"], r["result_count"]) for r in calls] == [
        ("no_match", 0),
        ("hit", 200),
    ]


def test_failed_classifier_is_unknown_not_ok():
    records = []

    def bad(tool, result):
        raise RuntimeError("nope")

    _run(_server(records, outcome=bad), [("search", {"q": "x"})])
    (r,) = [r for r in records if r["event"] == "tool_call"]
    assert r["outcome"] == "unknown"


def test_async_sink_is_awaited():
    records = []

    async def sink(record):
        await asyncio.sleep(0)
        records.append(record)

    server = mk_mcp_server([search], middleware=[UsageLogger(sink, name="t")])
    _run(server, [("search", {"q": "x"})])
    assert [r["event"] for r in records] == ["initialize", "tool_call"]


def test_result_count_only_for_lists():
    records = []

    def text() -> str:
        return "hello world"

    def table() -> dict:
        return {"matches": [], "total": 0}

    server = mk_mcp_server(
        [text, table, search], middleware=[UsageLogger(records.append, name="t")]
    )
    _run(server, [("text", {}), ("table", {}), ("search", {"q": "x"})])
    calls = [r for r in records if r["event"] == "tool_call"]
    assert [r["result_count"] for r in calls] == [None, None, 2]


def test_session_is_none_on_the_in_memory_transport_before_a_request():
    # Reading the session id must never *create* one (FastMCP caches a generated
    # id on the session if Context.session_id is read before a request exists).
    records = []
    _run(_server(records), [("search", {"q": "x"})])
    init, call = records[0], records[1]
    assert init["session"] is None  # initialize precedes any session
    assert call["session"] and call["request"]


def test_handshakes_can_be_switched_off():
    records = []
    _run(_server(records, handshakes=False), [("search", {"q": "x"})])
    assert [r["event"] for r in records] == ["tool_call"]


def test_redaction_and_no_args():
    records = []
    _run(
        _server(records, redact=("api_key",)),
        [("search", {"q": "x", "api_key": "s3cret"})],
    )
    (r,) = [r for r in records if r["event"] == "tool_call"]
    assert r["args"] == {"q": "x", "api_key": REDACTED}
    assert "s3cret" not in json.dumps(r)

    records = []
    _run(_server(records, include_args=False), [("search", {"q": "x"})])
    (r,) = [r for r in records if r["event"] == "tool_call"]
    assert "args" not in r


def test_args_are_capped():
    records = []
    _run(_server(records, max_args_chars=20), [("search", {"q": "y" * 100})])
    (r,) = [r for r in records if r["event"] == "tool_call"]
    assert r["args_truncated"] is True
    assert isinstance(r["args"], str) and len(r["args"]) <= 21


def test_custom_outcome_and_caller():
    records = []
    _run(
        _server(
            records,
            outcome=lambda tool, result: (
                "no_match" if not result.structured_content["result"] else "hit"
            ),
            caller=lambda: "someone@example.com",
        ),
        [("search", {"q": "none"}), ("search", {"q": "x"})],
    )
    calls = [r for r in records if r["event"] == "tool_call"]
    assert [r["outcome"] for r in calls] == ["no_match", "hit"]
    assert {r["caller"] for r in calls} == {"someone@example.com"}


def test_sink_failure_never_fails_the_call(caplog):
    def bad_sink(record):
        raise OSError("disk full")

    server = mk_mcp_server([search], middleware=[UsageLogger(bad_sink, name="t")])
    with caplog.at_level(logging.WARNING, logger="py2mcp.usage"):
        (result,) = _run(server, [("search", {"q": "x"})])
    assert result.data == ["x", "X"]  # the tool still ran and answered
    assert any("sink failed" in m for m in caplog.messages)


def test_tool_error_still_propagates_after_logging():
    records = []
    (err,) = _run(_server(records), [("boom", {"x": 1})])
    assert isinstance(err, ToolError)
    assert [r["outcome"] for r in records if r["event"] == "tool_call"] == ["error"]


def test_default_sink_is_the_user_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    logger = UsageLogger(name="My Conn")
    assert isinstance(logger.sink, JsonlSink)
    assert logger.sink.root == tmp_path / "py2mcp" / "usage" / "My_Conn"
    assert logger.sink.root.is_dir()
    assert logger.sink.retention_days == DFLT_RETENTION_DAYS
    assert default_usage_dir("x") == tmp_path / "py2mcp" / "usage" / "x"


def test_http_app_accepts_the_logger():
    app = mk_http_app(
        ["os.path:basename"], name="conn", middleware=UsageLogger([].append)
    )
    assert callable(app)


def test_token_caller_is_none_outside_a_request():
    assert token_caller() is None


def test_default_outcome_shapes():
    assert default_outcome("t", ToolResult(content="x")) == "ok"
    assert (
        default_outcome("t", ToolResult(structured_content={"result": []})) == "empty"
    )
    assert (
        default_outcome("t", ToolResult(structured_content={"result": None})) == "empty"
    )
    assert (
        default_outcome("t", ToolResult(structured_content={"result": {"a": 1}}))
        == "ok"
    )
    assert default_outcome("t", ToolResult(structured_content={"rows": []})) == "ok"
    assert default_outcome("t", ToolResult(content="x", is_error=True)) == "error"


# --- sinks ---------------------------------------------------------------------


def _rec(day, **kw):
    return {
        "id": kw.pop("id", day),
        "ts": f"{day}T12:00:00+00:00",
        "event": "tool_call",
        **kw,
    }


def test_jsonl_sink_writes_day_files_and_prunes(tmp_path):
    sink = JsonlSink(tmp_path / "usage", retention_days=7)
    today = date(2026, 10, 2)
    old = (today - timedelta(days=8)).isoformat()
    kept = (today - timedelta(days=6)).isoformat()
    sink(_rec(old))
    sink(_rec(kept))
    assert {p.name for p in sink.root.iterdir()} == {f"{old}.jsonl", f"{kept}.jsonl"}
    sink(_rec(today.isoformat(), tool="search"))  # new day -> prune
    assert {p.name for p in sink.root.iterdir()} == {f"{kept}.jsonl", f"{today}.jsonl"}
    lines = (sink.root / f"{today}.jsonl").read_text().splitlines()
    assert json.loads(lines[0])["tool"] == "search"


def test_jsonl_sink_prunes_at_construction_and_recreates_dir(tmp_path, caplog):
    root = tmp_path / "usage"
    root.mkdir()
    (root / "2020-01-01.jsonl").write_text("{}\n")
    sink = JsonlSink(root, retention_days=7)
    assert not (root / "2020-01-01.jsonl").exists()  # pruned at construction
    import shutil

    shutil.rmtree(root)
    sink(_rec("2026-10-02"))  # dir recreated on write
    assert (root / "2026-10-02.jsonl").exists()


def test_jsonl_sink_bad_dir_is_reported_not_raised(tmp_path, caplog):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with caplog.at_level(logging.ERROR, logger="py2mcp.usage"):
        sink = JsonlSink(blocker / "usage")  # cannot mkdir under a file
    assert any("cannot create" in m for m in caplog.messages)
    with pytest.raises(OSError):
        JsonlSink(blocker / "usage", strict=True)
    with pytest.raises(ValueError):
        JsonlSink(tmp_path, retention_days=-1)
    # a write still fails softly through the middleware's guard
    with pytest.raises(OSError):
        sink(_rec("2026-10-02"))


def test_jsonl_sink_retention_zero_keeps_today_only(tmp_path):
    sink = JsonlSink(tmp_path, retention_days=0)
    sink(_rec("2026-10-01"))
    sink(_rec("2026-10-02"))
    assert {p.name for p in tmp_path.glob("*.jsonl")} == {"2026-10-02.jsonl"}


def test_jsonl_sink_no_retention_keeps_everything(tmp_path):
    sink = JsonlSink(tmp_path, retention_days=None)
    sink(_rec("2020-01-01"))
    sink(_rec("2026-10-02"))
    assert len(list(tmp_path.glob("*.jsonl"))) == 2
    assert sink.prune() == []


def test_jsonl_sink_bad_timestamp_falls_back_to_today(tmp_path):
    sink = JsonlSink(tmp_path, retention_days=None)
    sink({"id": "x", "ts": "garbage"})
    (f,) = tmp_path.glob("*.jsonl")
    date.fromisoformat(f.stem)  # today's date


def test_mapping_sink_keys_by_day_and_id():
    store = {}
    sink = mapping_sink(store)
    sink(_rec("2026-10-02", id="abc"))
    assert store == {"2026-10-02/abc.json": _rec("2026-10-02", id="abc")}
    custom = {}
    mapping_sink(custom, key=lambda r: r["id"])(_rec("2026-10-02", id="k"))
    assert list(custom) == ["k"]


# --- reading back ------------------------------------------------------------------


def _populate(root):
    sink = JsonlSink(root, retention_days=None)
    sink(
        {
            "id": "h",
            "ts": "2026-10-01T08:00:00+00:00",
            "event": "initialize",
            "caller": "a",
        }
    )
    sink(
        _rec(
            "2026-10-01",
            id="1",
            caller="a",
            tool="search",
            outcome="ok",
            latency_ms=10.0,
        )
    )
    sink(
        _rec(
            "2026-10-02",
            id="2",
            caller="b",
            tool="search",
            outcome="empty",
            latency_ms=30.0,
        )
    )
    sink(
        _rec(
            "2026-10-02",
            id="3",
            caller="a",
            tool="boom",
            outcome="error",
            latency_ms=1.0,
        )
    )
    sink(
        _rec(
            "2026-10-03",
            id="4",
            caller="b",
            tool="search",
            outcome="ok",
            latency_ms=20.0,
        )
    )
    with open(root / "2026-10-03.jsonl", "a") as f:
        f.write("not json\n")  # a torn line must not hide the rest
    return sink


def test_iter_records_filters_by_day_and_skips_bad_lines(tmp_path):
    _populate(tmp_path)
    assert [r["id"] for r in iter_records(tmp_path)] == ["h", "1", "2", "3", "4"]
    assert [r["id"] for r in iter_records(tmp_path, since="2026-10-02")] == [
        "2",
        "3",
        "4",
    ]
    assert [
        r["id"] for r in iter_records(tmp_path, since="2026-10-02", until="2026-10-02")
    ] == ["2", "3"]
    assert [r["id"] for r in iter_records(tmp_path / "2026-10-03.jsonl")] == ["4"]
    with pytest.raises(FileNotFoundError):
        list(iter_records(tmp_path / "nope"))
    with pytest.raises(ValueError):
        list(iter_records(tmp_path, since="yesterday"))


def test_summarize_counts(tmp_path):
    _populate(tmp_path)
    s = summarize(iter_records(tmp_path))
    assert s["calls"] == 4 and s["handshakes"] == 1
    assert s["callers"] == {"a": 2, "b": 2}
    assert s["outcomes"] == {"ok": 2, "empty": 1, "error": 1}
    assert s["tools"]["search"] == {
        "calls": 3,
        "ok": 2,
        "empty": 1,
        "error": 0,
        "latency_ms_mean": 20.0,
        "latency_ms_max": 30.0,
    }
    assert s["tools"]["boom"]["error"] == 1
    assert s["days"] == {"2026-10-01": 1, "2026-10-02": 2, "2026-10-03": 1}
    assert (
        s["first"] == "2026-10-01T08:00:00+00:00"
        and s["last"] == "2026-10-03T12:00:00+00:00"
    )
    assert s["servers"] == {"(unnamed)": 4}
    text = format_summary(s)
    assert "search" in text and "calls: 4" in text
    assert summarize([])["calls"] == 0  # empty log is fine


def test_custom_labels_get_their_own_column():
    recs = [
        _rec("2026-10-02", id=str(i), tool="search", outcome=o, latency_ms=1.0)
        for i, o in enumerate(["ok", "no_match", "no_match"])
    ]
    s = summarize(recs)
    assert s["outcomes"]["no_match"] == 2 and s["tools"]["search"]["no_match"] == 2
    text = format_summary(s)
    header = [l for l in text.splitlines() if l.startswith("tools")][0]
    assert "no_match" in header
    row = [l for l in text.splitlines() if "search" in l][0]
    assert row.split()[1:5] == ["3", "1", "0", "0"]  # calls ok empty error ...


def test_cli_usage_subcommand(tmp_path, capsys):
    _populate(tmp_path)
    cli_main(["usage", str(tmp_path), "--since", "2026-10-02"])
    out = capsys.readouterr().out
    assert "calls: 3" in out
    cli_main(["usage", str(tmp_path), "--json"])
    assert json.loads(capsys.readouterr().out)["calls"] == 4
    cli_main(["usage", str(tmp_path), "--records", "--until", "2026-10-01"])
    lines = capsys.readouterr().out.splitlines()
    assert [json.loads(l)["id"] for l in lines] == ["h", "1"]
    with pytest.raises(SystemExit):
        cli_main(["usage", str(tmp_path / "missing")])


def test_cli_serving_form_is_unchanged(monkeypatch):
    # `py2mcp --ref ...` (no subcommand) must still reach serve_stdio.
    from py2mcp import serve as serve_mod

    captured = {}
    monkeypatch.setattr(
        serve_mod, "serve_stdio", lambda refs, **kw: captured.update(refs=refs, **kw)
    )
    cli_main(["--ref", "os.path:basename", "--name", "x"])
    assert captured["refs"] == ["os.path:basename"] and captured["name"] == "x"
