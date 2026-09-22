"""Tests for ``py2mcp.util`` — the pure, FastMCP-free helpers.

Focus is on ``claude_install_link`` / ``markdown_install_badge``, whose whole
contract is the exact string they produce: these links get pasted into READMEs
and handed to users, so a percent-encoding slip silently produces a link that
opens the modal with a mangled URL. The module's doctests are also run here,
since the repo's CI invokes pytest without ``--doctest-modules``.
"""

import doctest
import inspect
from urllib.parse import parse_qs, urlparse

import py2mcp.util
from py2mcp import claude_install_link, markdown_install_badge


def test_doctests_of_util_module():
    results = doctest.testmod(
        py2mcp.util, optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS
    )
    assert results.failed == 0


def test_install_link_exact_url():
    assert claude_install_link("snout", "https://example.com/api/snout_mcp/mcp") == (
        "https://claude.ai/customize/connectors?modal=add-custom-connector"
        "&connectorName=snout"
        "&connectorUrl=https%3A%2F%2Fexample.com%2Fapi%2Fsnout_mcp%2Fmcp"
    )


def test_install_link_admin_and_space_in_name():
    assert claude_install_link("my server", "https://x.io/mcp", admin=True) == (
        "https://claude.ai/admin-settings/connectors?modal=add-custom-connector"
        "&connectorName=my%20server"
        "&connectorUrl=https%3A%2F%2Fx.io%2Fmcp"
    )


def test_admin_flag_is_keyword_only():
    params = inspect.signature(claude_install_link).parameters
    assert params["admin"].kind is inspect.Parameter.KEYWORD_ONLY
    assert params["admin"].default is False


def test_ampersand_in_name_does_not_break_query_string():
    """A raw ``&`` would inject a bogus parameter; it must be percent-encoded."""
    url = claude_install_link("a&b=c", "https://x.io/mcp")
    query = parse_qs(urlparse(url).query, strict_parsing=True)
    assert query["connectorName"] == ["a&b=c"]
    assert query["connectorUrl"] == ["https://x.io/mcp"]
    assert set(query) == {"modal", "connectorName", "connectorUrl"}


def test_round_trips_through_url_parsing():
    name, mcp_url = "café été", "https://x.io/mcp?a=1&b=2"
    query = parse_qs(urlparse(claude_install_link(name, mcp_url)).query)
    assert query["connectorName"] == [name]
    assert query["connectorUrl"] == [mcp_url]


def test_markdown_badge_wraps_the_link():
    name, mcp_url = "snout", "https://x.io/mcp"
    assert markdown_install_badge(name, mcp_url) == (
        f"[Add {name} to Claude]({claude_install_link(name, mcp_url)})"
    )


def test_markdown_badge_forwards_admin():
    assert "admin-settings" in markdown_install_badge(
        "snout", "https://x.io/mcp", admin=True
    )


def test_both_names_are_exported():
    assert {"claude_install_link", "markdown_install_badge"} <= set(py2mcp.__all__)
