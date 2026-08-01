"""Tests for the ``instructions=`` hook threaded through the server builders.

``instructions`` becomes FastMCP's server-level instructions (shown to the model
without a tool call). These verify it's attached and forwarded, and that the
no-instructions path stays unset.
"""

from py2mcp import mk_mcp_server, mk_mcp_from_refs, mk_mcp_from_store
from py2mcp.http import mk_http_app


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


def test_instructions_attached():
    server = mk_mcp_server([add], instructions="I turn text into audio.")
    assert server.instructions == "I turn text into audio."


def test_no_instructions_leaves_it_unset():
    server = mk_mcp_server([add])
    assert not server.instructions  # None or "" — FastMCP default


def test_mk_mcp_from_refs_forwards_instructions():
    server = mk_mcp_from_refs(["os.path:basename"], name="paths", instructions="Paths.")
    assert server.instructions == "Paths."


def test_mk_mcp_from_store_forwards_instructions():
    server = mk_mcp_from_store({}, name="item", instructions="A store.")
    assert server.instructions == "A store."


def test_mk_http_app_forwards_instructions(monkeypatch):
    from py2mcp import http as http_mod

    captured = {}

    class _DummyServer:
        def http_app(self, **kwargs):
            return object()

    def _fake_mk(refs, **kwargs):
        captured.update(kwargs)
        return _DummyServer()

    monkeypatch.setattr(http_mod, "mk_mcp_from_refs", _fake_mk)
    mk_http_app(["os.path:basename"], name="conn", instructions="Hello.")
    assert captured["instructions"] == "Hello."


class _RunSpyServer:
    """A server stand-in that records forwarded kwargs and no-ops ``run``."""

    def run(self, **kwargs):  # noqa: D401
        return None


def test_serve_http_forwards_instructions(monkeypatch):
    from py2mcp import http as http_mod

    captured = {}

    def _fake_mk(refs, **kwargs):
        captured.update(kwargs)
        return _RunSpyServer()

    monkeypatch.setattr(http_mod, "mk_mcp_from_refs", _fake_mk)
    http_mod.serve_http(["os.path:basename"], name="conn", instructions="Serve me.")
    assert captured["instructions"] == "Serve me."


def test_serve_stdio_forwards_instructions(monkeypatch):
    from py2mcp import serve as serve_mod

    captured = {}

    def _fake_mk(refs, **kwargs):
        captured.update(kwargs)
        return _RunSpyServer()

    monkeypatch.setattr(serve_mod, "mk_mcp_from_refs", _fake_mk)
    serve_mod.serve_stdio(["os.path:basename"], name="conn", instructions="Stdio me.")
    assert captured["instructions"] == "Stdio me."
