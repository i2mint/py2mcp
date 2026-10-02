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
        assert len(r["id"]) == 32


def test_is_error_result_is_an_error_outcome():
    records = []
    _run(_server(records), [("soft_fail", {"x": 1})])
    (r,) = [r for r in records if r["event"] == "tool_call"]
    assert r["outcome"] == "error"
    assert r["error"] == "nope"


def test_handshake_is_recorded_and_flagged():
    records = []
    _run(_server(records), [("search", {"q": "x"})])
    init = [r for r in records if r["event"] == "initialize"]
    assert len(init) == 1
    assert init[0]["client"]  # the fastmcp client's name
    assert init[0]["protocol"]
    assert "tool" not in init[0]


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
    text = format_summary(s)
    assert "search" in text and "calls: 4" in text
    assert summarize([])["calls"] == 0  # empty log is fine


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


def test_cli_serving_form_is_unchanged(monkeypatch):
    # `py2mcp --ref ...` (no subcommand) must still reach serve_stdio.
    from py2mcp import serve as serve_mod

    captured = {}
    monkeypatch.setattr(
        serve_mod, "serve_stdio", lambda refs, **kw: captured.update(refs=refs, **kw)
    )
    cli_main(["--ref", "os.path:basename", "--name", "x"])
    assert captured["refs"] == ["os.path:basename"] and captured["name"] == "x"
