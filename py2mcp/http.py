"""Serve a py2mcp ``FastMCP`` server over **Streamable HTTP** with optional
OAuth 2.1 — the *remote* counterpart to :mod:`py2mcp.serve` (stdio).

A *remote* MCP server (e.g. a claude.ai custom connector) is reached over public
HTTPS from the vendor's cloud and authenticates with **OAuth 2.1**. Per the MCP
authorization spec the MCP server is an OAuth 2.1 **resource server** — it
*validates* bearer tokens minted by a **managed identity provider** (the
authorization server) and **never issues tokens itself**. Two hard rules fall out
of that and are enforced here by construction:

- **Audience binding (RFC 8707).** The verifier checks the token's ``aud`` equals
  *this* server's resource id, so a token minted for another service cannot be
  replayed here (the confused-deputy defense).
- **No token passthrough.** This layer only *verifies* the inbound token; it never
  forwards it upstream. Any upstream call your tools make must use their own
  credentials.

It wraps FastMCP's native machinery (no transport/OAuth code is reinvented):

- :func:`mk_auth_provider` — an auth-config dict → a
  ``fastmcp.server.auth.RemoteAuthProvider`` (a ``JWTVerifier`` resource server
  that validates the IdP's JWTs and publishes the RFC 9728
  ``/.well-known/oauth-protected-resource`` document pointing at the IdP).
- :func:`mk_http_app` — build the server (via :func:`py2mcp.mk_mcp_from_refs`),
  attach the auth provider, and return a Streamable-HTTP **ASGI app** to run under
  any ASGI server (uvicorn, gunicorn, a serverless adapter).
- :func:`serve_http` — build and *run* it (blocking), for a self-hosted process.

``coact``'s ``claude-remote-connector`` publish target scaffolds a deployable
service around these — coact writes packaging, py2mcp builds and serves the MCP
server (the same division of labour as the stdio ``.mcpb`` path).
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Optional

from py2mcp.main import mk_mcp_from_refs
from py2mcp.serve import DFLT_SERVER_NAME

#: Auth ``type`` values :func:`mk_auth_provider` understands. ``'jwt'`` is the
#: vendor-neutral resource-server pattern (validate a managed IdP's JWTs);
#: managed-provider shortcuts (auth0/workos/...) can be added as new types.
SUPPORTED_AUTH_TYPES = ("jwt",)

#: Default Streamable-HTTP transport (the current remote MCP transport).
DFLT_TRANSPORT = "streamable-http"


def mk_auth_provider(auth: Optional[dict]) -> Optional[Any]:
    """Build a FastMCP **resource-server** auth provider from an auth-config dict.

    ``auth`` is ``None``/falsy (no auth) or a dict with a ``type`` key:

    ``type='jwt'`` (default) — validate JWTs issued by a managed IdP. Keys:

    - ``jwks_uri`` *or* ``public_key`` — where to get the IdP's signing key(s).
    - ``issuer`` — the IdP issuer URL (the token's ``iss``).
    - ``audience`` (**required**) — **this** server's resource id (the token's
      ``aud``). RFC 8707 audience binding is mandatory: it stops a token minted for
      another service being replayed here (the confused-deputy defense), so this
      helper refuses to build a verifier that would skip it.
    - ``authorization_servers`` (or a single ``issuer``) — IdP issuer URL(s)
      advertised in the RFC 9728 protected-resource metadata.
    - ``base_url`` — this server's public base URL.
    - ``required_scopes`` (optional) — scopes every request must carry.

    Returns a ``RemoteAuthProvider`` (a resource server), or ``None`` when ``auth``
    is falsy. Raises ``ValueError`` on an unknown ``type`` or a missing required key.
    Building the provider performs **no network I/O** (key fetching is lazy, on the
    first request), so this is safe to call at scaffold/import time.
    """
    if not auth:
        return None
    if not isinstance(auth, dict):
        raise ValueError("auth must be a dict (or None), e.g. {'type': 'jwt', ...}")
    auth_type = auth.get("type", "jwt")
    if auth_type != "jwt":
        raise ValueError(
            f"Unsupported auth type {auth_type!r}. Supported: "
            f"{', '.join(SUPPORTED_AUTH_TYPES)}. Use 'jwt' for the resource-server "
            "pattern (validate a managed IdP's JWTs); managed-provider shortcuts "
            "can be added as new types."
        )

    from fastmcp.server.auth import RemoteAuthProvider
    from fastmcp.server.auth.providers.jwt import JWTVerifier

    jwks_uri = auth.get("jwks_uri")
    public_key = auth.get("public_key")
    if not (jwks_uri or public_key):
        raise ValueError(
            "jwt auth needs 'jwks_uri' (or 'public_key') to validate token signatures."
        )
    base_url = auth.get("base_url")
    if not base_url:
        raise ValueError(
            "jwt auth needs 'base_url' (this server's public base URL, for the "
            "RFC 9728 protected-resource metadata)."
        )
    audience = auth.get("audience")
    if not audience:
        raise ValueError(
            "jwt auth needs 'audience' (this server's resource id). Without it the "
            "token's audience is NOT validated, which re-opens the confused-deputy "
            "vulnerability (a token minted for another service could be replayed "
            "here) — RFC 8707 audience binding is mandatory for an MCP resource "
            "server. Set it to this connector's public resource URL."
        )
    authorization_servers = auth.get("authorization_servers")
    if not authorization_servers and auth.get("issuer"):
        authorization_servers = [auth["issuer"]]
    if not authorization_servers:
        raise ValueError(
            "jwt auth needs 'authorization_servers' (or 'issuer') — the managed IdP "
            "that issues tokens, advertised via RFC 9728 discovery."
        )
    required_scopes = auth.get("required_scopes")

    verifier = JWTVerifier(
        jwks_uri=jwks_uri,
        public_key=public_key,
        issuer=auth.get("issuer"),
        audience=audience,
        required_scopes=required_scopes,
        base_url=base_url,
    )
    return RemoteAuthProvider(
        token_verifier=verifier,
        authorization_servers=list(authorization_servers),
        base_url=base_url,
        scopes_supported=required_scopes,
    )


def mk_http_app(
    refs: Iterable[str],
    *,
    name: str = DFLT_SERVER_NAME,
    auth: Optional[dict] = None,
    input_trans: Optional[Callable[[dict], dict]] = None,
    transport: str = DFLT_TRANSPORT,
    path: Optional[str] = None,
    stateless_http: Optional[bool] = None,
) -> Any:
    """Build a Streamable-HTTP **ASGI app** from ``refs`` (+ optional OAuth).

    Returns the ASGI application (a Starlette app), so any ASGI server can run it::

        # server/app.py
        from py2mcp.http import mk_http_app
        app = mk_http_app(['mypkg.tools:summarize'], name='My Connector', auth=AUTH)
        # then:  uvicorn server.app:app --host 0.0.0.0 --port 8000

    ``auth`` is resolved by :func:`mk_auth_provider` (``None`` → no auth; a remote
    connector should always set it). ``stateless_http=True`` is recommended behind
    a load balancer (MCP sessions are stateful, so default in-memory sessions break
    across replicas — go stateless or externalize session state). Builds the app
    with **no network I/O**.
    """
    provider = mk_auth_provider(auth)
    server = mk_mcp_from_refs(refs, name=name, input_trans=input_trans, auth=provider)
    http_kwargs: dict[str, Any] = {"transport": transport}
    if path is not None:
        http_kwargs["path"] = path
    if stateless_http is not None:
        http_kwargs["stateless_http"] = stateless_http
    return server.http_app(**http_kwargs)


def serve_http(
    refs: Iterable[str],
    *,
    name: str = DFLT_SERVER_NAME,
    host: str = "127.0.0.1",
    port: int = 8000,
    auth: Optional[dict] = None,
    input_trans: Optional[Callable[[dict], dict]] = None,
    transport: str = DFLT_TRANSPORT,
    stateless_http: Optional[bool] = None,
) -> None:
    """Build and **run** a Streamable-HTTP MCP server (blocking) via FastMCP/uvicorn.

    For a self-hosted process. Binds ``127.0.0.1`` by default — expose a public
    interface only behind a TLS-terminating reverse proxy (a remote connector must
    be reachable over public **HTTPS**, and binding locally is the spec's
    DNS-rebinding-safe default). ``auth`` is resolved by :func:`mk_auth_provider`.
    """
    provider = mk_auth_provider(auth)
    server = mk_mcp_from_refs(refs, name=name, input_trans=input_trans, auth=provider)
    run_kwargs: dict[str, Any] = {"transport": transport, "host": host, "port": port}
    if stateless_http is not None:
        run_kwargs["stateless_http"] = stateless_http
    server.run(**run_kwargs)
