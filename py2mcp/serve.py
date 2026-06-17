"""Serve a py2mcp ``FastMCP`` server over **stdio** — the runner a packaged
integration launches.

:func:`py2mcp.mk_mcp_server` / :func:`py2mcp.mk_mcp_from_refs` build a server
*object* but deliberately leave *running* it to the caller (the only run hint in
``main`` is a comment). This module adds the thin "actually serve it over stdio"
layer plus a small JSON-config loader, so a one-click bundle (e.g. a Claude
Desktop ``.mcpb`` Desktop Extension) can point its ``manifest.json`` at::

    python -m py2mcp --config ${__dirname}/server/py2mcp_config.json

and get a live MCP server. The config is just ``{"name": ..., "refs": [...]}``
where each ref is a ``'module:function'`` string resolved by
:func:`py2mcp.util.import_object`.

stdio note: an MCP stdio server speaks newline-delimited JSON-RPC on
stdout, so nothing else may be written there. ``FastMCP``'s ``run`` handles this;
keep application logging on stderr.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from py2mcp.main import mk_mcp_from_refs

#: Default server name when neither a config nor ``--name`` supplies one.
DFLT_SERVER_NAME = "py2mcp Server"


def load_server_config(path: str | Path) -> dict:
    """Load a server config JSON of the form ``{"name": str, "refs": [str, ...]}``.

    Raises ``ValueError`` if the file is not a JSON object carrying a ``refs``
    list — an actionable error beats a server that starts with no tools.
    """
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or not isinstance(data.get("refs"), list):
        raise ValueError(
            f"py2mcp server config {str(path)!r} must be a JSON object with a "
            '"refs" list, e.g. {"name": "My Tools", "refs": ["pkg.mod:func"]}.'
        )
    return data


def resolve_server_config(
    *,
    config: Optional[str | Path] = None,
    refs: Iterable[str] = (),
    name: Optional[str] = None,
) -> tuple[list[str], str]:
    """Merge a config file and explicit ``refs``/``name`` into ``(refs, name)``.

    Refs from ``--ref`` are appended after any from the config file; an explicit
    ``name`` wins over the config's. Pure (no I/O beyond reading ``config``), so
    it is unit-testable without standing up a server.

    >>> resolve_server_config(refs=['os.path:basename'], name='Paths')
    (['os.path:basename'], 'Paths')
    """
    cfg_refs: list[str] = []
    cfg_name: Optional[str] = None
    if config is not None:
        cfg = load_server_config(config)
        cfg_refs = list(cfg.get("refs") or [])
        cfg_name = cfg.get("name")
    merged_refs = cfg_refs + list(refs)
    if not merged_refs:
        raise ValueError(
            "No tool references to serve. Provide a --config file with a 'refs' "
            "list and/or one or more --ref 'module:function' arguments."
        )
    return merged_refs, (name or cfg_name or DFLT_SERVER_NAME)


def serve_stdio(
    refs: Iterable[str],
    *,
    name: str = DFLT_SERVER_NAME,
    input_trans: Optional[Callable[[dict], dict]] = None,
) -> None:
    """Build an MCP server from ``'module:function'`` refs and run it over stdio.

    Blocks, serving the MCP protocol on stdin/stdout until the host disconnects.
    Thin wrapper over :func:`py2mcp.mk_mcp_from_refs` + ``FastMCP.run`` so that
    packaged integrations have one command to launch.
    """
    server = mk_mcp_from_refs(refs, name=name, input_trans=input_trans)
    server.run(transport="stdio")


def main(argv: Optional[list[str]] = None) -> None:
    """CLI: ``python -m py2mcp --config cfg.json`` (or ``--ref mod:func ...``)."""
    parser = argparse.ArgumentParser(
        prog="py2mcp",
        description="Serve an MCP server from 'module:function' refs — over stdio "
        "(default) or Streamable HTTP (--http).",
    )
    parser.add_argument(
        "--config",
        help='Path to a JSON config: {"name": str, "refs": ["module:function", ...]}.',
    )
    parser.add_argument(
        "--ref",
        action="append",
        dest="refs",
        default=[],
        metavar="module:function",
        help="A tool reference to expose (repeatable; merged after --config refs).",
    )
    parser.add_argument(
        "--name", default=None, help="Server name (overrides the config's name)."
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve over Streamable HTTP instead of stdio (a remote MCP server). "
        "OAuth/host/port come from the config's 'auth'/'host'/'port' keys.",
    )
    parser.add_argument(
        "--host", default=None, help="HTTP bind host (with --http; default 127.0.0.1)."
    )
    parser.add_argument(
        "--port", type=int, default=None, help="HTTP bind port (with --http; default 8000)."
    )
    args = parser.parse_args(argv)
    try:
        refs, name = resolve_server_config(
            config=args.config, refs=args.refs, name=args.name
        )
    except (ValueError, OSError) as e:
        parser.error(str(e))

    if args.http:
        from py2mcp.http import serve_http

        cfg = load_server_config(args.config) if args.config else {}
        try:
            serve_http(
                refs,
                name=name,
                host=args.host or cfg.get("host") or "127.0.0.1",
                port=args.port or cfg.get("port") or 8000,
                auth=cfg.get("auth"),
            )
        except (ValueError, OSError) as e:
            parser.error(str(e))
    else:
        serve_stdio(refs, name=name)


if __name__ == "__main__":
    main()
