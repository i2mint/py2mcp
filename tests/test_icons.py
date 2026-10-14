"""Server icons reach FastMCP (and so the MCP ``serverInfo``) from every builder."""

import pytest
from mcp.types import Icon

from py2mcp import mk_mcp_from_refs, mk_mcp_server
from py2mcp.http import mk_http_app


def add(a: int, b: int) -> int:
    return a + b


def test_no_icons_by_default():
    assert not mk_mcp_server(add).icons


@pytest.mark.parametrize(
    "icons",
    [
        "data:image/png;base64,AAAA",
        ["data:image/png;base64,AAAA"],
        {"src": "data:image/png;base64,AAAA", "mimeType": "image/png"},
        [Icon(src="data:image/png;base64,AAAA", mimeType="image/png")],
    ],
)
def test_every_icon_spelling_lands_on_the_server(icons):
    [icon] = mk_mcp_server(add, icons=icons).icons
    assert icon.src == "data:image/png;base64,AAAA"


def test_from_refs_forwards_icons():
    [icon] = mk_mcp_from_refs(["os.path:basename"], icons="https://x/i.png").icons
    assert icon.src == "https://x/i.png"


def test_http_app_builds_with_icons():
    assert callable(mk_http_app(["os.path:basename"], icons="https://x/i.png"))


def test_a_wrong_icon_type_is_refused():
    with pytest.raises(TypeError, match="an icon is"):
        mk_mcp_server(add, icons=[42])
