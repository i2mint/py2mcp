"""Keyword-only defaults must survive ``from __future__ import annotations``.

This module deliberately carries the future import, so the functions below have
*string* annotations exactly as a caller's module would. That is the whole point:
the defect pinned here is invisible without it.

Under fastmcp < 3.2 the schema layer built its validator from the unresolved
strings and every ``KEYWORD_ONLY`` default was lost -- calling ``kwonly`` with
only ``a`` failed with "Missing required keyword only argument" for ``b`` and
``c``. ``list_tools`` and the generated JSON schema both looked completely
correct, so the only way to see it was to *call* a tool, which is how it reached
a release. fastmcp 3.2.0 resolves annotations itself; the floor in
``pyproject.toml`` is what keeps that true, and these tests are what make
lowering that floor fail loudly instead of silently.

See https://github.com/i2mint/py2mcp/issues/12.
"""

from __future__ import annotations

import asyncio

from py2mcp import mk_mcp_from_refs, mk_mcp_server


def kwonly(a: str, *, b: str = "bee", c: int = 3) -> str:
    """A verb shaped like the ones py2mcp exists to expose."""
    return f"{a}|{b}|{c}"


def positional_default(a: str, b: str = "bee") -> str:
    """The control: positional-or-keyword defaults were never affected."""
    return f"{a}|{b}"


def test_the_annotations_really_are_lazy():
    """Guard the guard: without the future import these tests prove nothing."""
    assert kwonly.__annotations__["a"] == "str"


def test_keyword_only_defaults_are_not_required_of_the_caller():
    mcp = mk_mcp_server([kwonly], name="probe")
    result = asyncio.run(mcp.call_tool("kwonly", {"a": "x"}))
    assert result.structured_content == {"result": "x|bee|3"}


def test_keyword_only_defaults_can_still_be_overridden():
    mcp = mk_mcp_server([kwonly], name="probe")
    result = asyncio.run(mcp.call_tool("kwonly", {"a": "x", "c": 9}))
    assert result.structured_content == {"result": "x|bee|9"}


def test_positional_defaults_are_unaffected():
    mcp = mk_mcp_server([positional_default], name="probe")
    result = asyncio.run(mcp.call_tool("positional_default", {"a": "x"}))
    assert result.structured_content == {"result": "x|bee"}


def test_the_same_holds_through_mk_mcp_from_refs(tmp_path, monkeypatch):
    """The ref path is the one a caller cannot reach into to fix themselves.

    Written against a module on disk rather than this one, because a ref is
    resolved by import and the test suite is not an importable package. The
    module carries the future import for the same reason this one does.
    """
    module = tmp_path / "lazy_verbs.py"
    module.write_text(
        "from __future__ import annotations\n\n\n"
        'def kwonly(a: str, *, b: str = "bee", c: int = 3) -> str:\n'
        '    return f"{a}|{b}|{c}"\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    mcp = mk_mcp_from_refs(["lazy_verbs:kwonly"], name="probe")
    result = asyncio.run(mcp.call_tool("kwonly", {"a": "x"}))
    assert result.structured_content == {"result": "x|bee|3"}
