"""Per-tool MCP annotations on ``mk_mcp_server`` / ``mk_mcp_from_refs``."""

import asyncio

from py2mcp import mk_mcp_from_refs, mk_mcp_server


def _tools(server):
    return {t.name: t for t in asyncio.run(server.list_tools())}


def read(): ...
def wipe(): ...


def test_mapping_by_name():
    tools = _tools(
        mk_mcp_server(
            [read, wipe],
            annotations={"read": {"readOnlyHint": True, "openWorldHint": False}},
        )
    )
    assert tools["read"].annotations.readOnlyHint is True
    assert tools["read"].annotations.openWorldHint is False
    assert tools["wipe"].annotations is None


def test_callable_sees_original_function():
    ann = lambda f: {"destructiveHint": True} if f.__name__ == "wipe" else None
    tools = _tools(mk_mcp_server([read, wipe], annotations=ann, input_trans=lambda d: d))
    assert tools["wipe"].annotations.destructiveHint is True
    assert tools["read"].annotations is None


def test_from_refs():
    server = mk_mcp_from_refs(
        ["os.path:basename"], annotations={"basename": {"readOnlyHint": True}}
    )
    assert _tools(server)["basename"].annotations.readOnlyHint is True


def test_default_unchanged():
    assert _tools(mk_mcp_server(read))["read"].annotations is None
