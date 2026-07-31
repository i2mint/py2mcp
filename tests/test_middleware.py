"""Tests for the ``middleware=`` hook threaded through the server builders.

py2mcp attaches FastMCP middleware at construction — the seam for cross-cutting
concerns (metering, logging, rate limiting) that must wrap every tool call. These
verify the hook is (a) attached by every builder and (b) actually fires around a
real tool invocation (via an in-memory client), plus the single-vs-list
normalization. See i2mint/py2mcp#6.
"""

import asyncio

from fastmcp import Client
from fastmcp.server.middleware import Middleware

from py2mcp import mk_mcp_server, mk_mcp_from_refs
from py2mcp.http import mk_http_app


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


class _Recorder(Middleware):
    """A middleware that records the name of every tool call it wraps."""

    def __init__(self):
        self.calls = []

    async def on_call_tool(self, context, call_next):
        self.calls.append(context.message.name)
        return await call_next(context)


def test_single_middleware_is_attached():
    rec = _Recorder()
    server = mk_mcp_server([add], middleware=rec)  # single, not a list
    assert rec in server.middleware


def test_list_of_middleware_is_attached():
    a, b = _Recorder(), _Recorder()
    server = mk_mcp_server([add], middleware=[a, b])
    assert a in server.middleware and b in server.middleware


def test_no_middleware_still_builds():
    server = mk_mcp_server([add])
    assert isinstance(server.middleware, list)  # only FastMCP's own defaults


def test_middleware_fires_around_a_tool_call():
    # The acceptance test from issue #6: the hook actually wraps the call.
    rec = _Recorder()
    server = mk_mcp_server([add], middleware=[rec])

    async def go():
        async with Client(server) as client:
            return await client.call_tool("add", {"a": 2, "b": 3})

    result = asyncio.run(go())
    assert result.data == 5  # the tool ran
    assert rec.calls == ["add"]  # ... and the middleware saw it


def test_mk_mcp_from_refs_forwards_middleware():
    rec = _Recorder()
    server = mk_mcp_from_refs(["os.path:basename"], name="paths", middleware=rec)
    assert rec in server.middleware


def test_mk_http_app_accepts_middleware():
    rec = _Recorder()
    app = mk_http_app(["os.path:basename"], name="conn", middleware=[rec])
    assert callable(app)  # a real ASGI app built with the middleware attached


def test_serve_http_forwards_middleware(monkeypatch):
    # serve_http is blocking; capture the forwarded kwarg without binding a port.
    from py2mcp import http as http_mod

    captured = {}

    class _DummyServer:
        def run(self, **kwargs):
            captured["ran"] = True

    def _fake_mk(refs, **kwargs):
        captured.update(kwargs)
        return _DummyServer()

    monkeypatch.setattr(http_mod, "mk_mcp_from_refs", _fake_mk)
    rec = _Recorder()
    http_mod.serve_http(["os.path:basename"], name="conn", middleware=rec)
    assert captured["middleware"] is rec
    assert captured["ran"] is True
