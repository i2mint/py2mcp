"""General utilities for py2mcp."""

from importlib import import_module
from typing import Any, MutableMapping, Callable, TypeVar
from collections.abc import Iterator
from urllib.parse import quote, urlencode

KT = TypeVar("KT")
VT = TypeVar("VT")


def import_object(ref: str) -> Any:
    """Resolve a ``'module.path:attr'`` (preferred) or ``'module.path.attr'`` reference.

    Useful for building MCP servers from configuration strings (e.g. tool
    references declared in a file), so callers don't reimplement the
    ``importlib`` dance.

    >>> import_object('json:dumps')  # doctest: +ELLIPSIS
    <function dumps at ...>
    >>> import_object('os.path.join')  # doctest: +ELLIPSIS
    <function join at ...>
    """
    if ":" in ref:
        module_name, _, attr = ref.partition(":")
    else:
        module_name, _, attr = ref.rpartition(".")
    if not module_name or not attr:
        raise ValueError(
            f"Invalid object reference {ref!r}; expected 'module:attr' "
            f"or 'module.path.attr'."
        )
    obj = import_module(module_name)
    for part in attr.split("."):
        obj = getattr(obj, part)
    return obj


def claude_install_link(name: str, mcp_url: str, *, admin: bool = False) -> str:
    """Prefilled "Add custom connector" link for claude.ai.

    There is no true one-click install for an unlisted MCP server (listing
    requires Anthropic review), but this link opens the add-connector modal with
    the name and URL already filled in, so the user only has to confirm — which
    beats "go to Settings, find Connectors, paste this long URL".

    Args:
        name: Connector name to prefill (what the user will see in their list).
        mcp_url: Full URL of the MCP endpoint, e.g. ``https://host/api/x/mcp``.
        admin: Target the org-wide install page instead of the per-user one.
            Use it when an admin is rolling the connector out to a whole
            workspace; the default (``False``) is the personal install.

    Returns:
        The claude.ai URL, safe to paste into a README or a chat message.

    >>> claude_install_link('snout', 'https://example.com/api/snout_mcp/mcp')
    'https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=snout&connectorUrl=https%3A%2F%2Fexample.com%2Fapi%2Fsnout_mcp%2Fmcp'

    Names and URLs are percent-encoded, so spaces (and ``&``) can't break the
    query string:

    >>> claude_install_link('my server', 'https://x.io/mcp', admin=True)
    'https://claude.ai/admin-settings/connectors?modal=add-custom-connector&connectorName=my%20server&connectorUrl=https%3A%2F%2Fx.io%2Fmcp'

    Note that the link is a convenience, not an access grant: if the server is an
    OAuth resource server with an allowlist, a user who isn't on it can follow
    the link, complete the flow, and still be refused. Custom connectors are also
    a paid-plan feature, so the link goes nowhere for a Free-plan user.
    """
    path = "admin-settings" if admin else "customize"
    params = urlencode(
        {
            "modal": "add-custom-connector",
            "connectorName": name,
            "connectorUrl": mcp_url,
        },
        quote_via=quote,
    )
    return f"https://claude.ai/{path}/connectors?{params}"


def markdown_install_badge(name: str, mcp_url: str, *, admin: bool = False) -> str:
    """Markdown link that installs an MCP server as a claude.ai connector.

    The dominant use of :func:`claude_install_link` is pasting one into a README,
    so this saves writing the same link syntax around it. Arguments are those of
    :func:`claude_install_link`.

    >>> markdown_install_badge('snout', 'https://x.io/mcp')
    '[Add snout to Claude](https://claude.ai/customize/connectors?modal=add-custom-connector&connectorName=snout&connectorUrl=https%3A%2F%2Fx.io%2Fmcp)'
    """
    return f"[Add {name} to Claude]({claude_install_link(name, mcp_url, admin=admin)})"


def _store_to_funcs(
    store: MutableMapping[KT, VT],
    *,
    singular: str = "item",
    plural: str = "",
) -> Iterator[tuple[str, Callable]]:
    """Generate CRUD functions from a MutableMapping.

    >>> store = {'a': 1, 'b': 2}
    >>> funcs = dict(_store_to_funcs(store, singular='item'))
    >>> sorted(funcs['list_items']())
    ['a', 'b']
    >>> funcs['get_item']('a')
    1
    """
    plural = plural or f"{singular}s"

    def list_items() -> list[KT]:
        """List all keys."""
        return list(store.keys())

    def get_item(key: KT) -> VT:
        """Get a value by key."""
        return store[key]

    def set_item(key: KT, value: VT) -> str:
        """Set a value."""
        store[key] = value
        return f"Set {singular} '{key}'"

    def delete_item(key: KT) -> str:
        """Delete a value."""
        del store[key]
        return f"Deleted {singular} '{key}'"

    for func, func_name in [
        (list_items, f"list_{plural}"),
        (get_item, f"get_{singular}"),
        (set_item, f"set_{singular}"),
        (delete_item, f"delete_{singular}"),
    ]:
        func.__name__ = func_name
        yield func_name, func


def store_to_funcs(
    store: MutableMapping[KT, VT],
    *,
    name: str = "item",
    plural: str = "",
) -> list[Callable]:
    """Convert a MutableMapping into CRUD functions.

    >>> projects = {'p1': {'name': 'Project 1'}}
    >>> funcs = store_to_funcs(projects, name='project')
    >>> len(funcs)
    4
    >>> [f.__name__ for f in funcs]
    ['list_projects', 'get_project', 'set_project', 'delete_project']
    """
    return [func for _, func in _store_to_funcs(store, singular=name, plural=plural)]
