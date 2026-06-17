"""Tests for the remote (Streamable-HTTP + OAuth) serving layer.

All offline: building the resource-server auth provider and the ASGI app performs
no network I/O (JWKS fetching is lazy, on the first request), so these construct
real fastmcp objects without standing up a server or contacting an IdP. The
blocking ``serve_http`` is exercised only via a monkeypatched CLI (no port bind).
"""

import json

import pytest

from py2mcp.http import mk_auth_provider, mk_http_app

# A complete, fake JWT resource-server config (no network at construction).
_AUTH = {
    "type": "jwt",
    "jwks_uri": "https://idp.example.com/.well-known/jwks.json",
    "issuer": "https://idp.example.com",
    "audience": "https://conn.example.com/mcp",
    "authorization_servers": ["https://idp.example.com"],
    "base_url": "https://conn.example.com",
    "required_scopes": ["mcp:read"],
}


# --- mk_auth_provider --------------------------------------------------------


def test_no_auth_returns_none():
    assert mk_auth_provider(None) is None
    assert mk_auth_provider({}) is None  # falsy dict = no auth


def test_jwt_auth_builds_resource_server():
    from fastmcp.server.auth import RemoteAuthProvider

    provider = mk_auth_provider(_AUTH)
    assert isinstance(provider, RemoteAuthProvider)


def test_issuer_derives_authorization_servers():
    auth = {k: v for k, v in _AUTH.items() if k != "authorization_servers"}
    provider = mk_auth_provider(auth)  # issuer alone is enough
    assert provider is not None


def test_missing_signing_key_raises():
    auth = {k: v for k, v in _AUTH.items() if k not in ("jwks_uri", "public_key")}
    with pytest.raises(ValueError, match="jwks_uri"):
        mk_auth_provider(auth)


def test_missing_base_url_raises():
    auth = {k: v for k, v in _AUTH.items() if k != "base_url"}
    with pytest.raises(ValueError, match="base_url"):
        mk_auth_provider(auth)


def test_missing_authorization_servers_raises():
    auth = {
        k: v
        for k, v in _AUTH.items()
        if k not in ("authorization_servers", "issuer")
    }
    with pytest.raises(ValueError, match="authorization_servers"):
        mk_auth_provider(auth)


def test_unknown_auth_type_raises():
    with pytest.raises(ValueError, match="Unsupported auth type"):
        mk_auth_provider({"type": "magic"})


def test_non_dict_auth_raises():
    with pytest.raises(ValueError, match="must be a dict"):
        mk_auth_provider("oauth")


# --- mk_http_app -------------------------------------------------------------


def test_http_app_without_auth_is_asgi_app():
    app = mk_http_app(["os.path:basename"], name="conn")
    # a Starlette ASGI app: callable, with routes
    assert callable(app)
    assert hasattr(app, "routes")


def test_http_app_with_auth_builds():
    app = mk_http_app(["os.path:basename"], name="conn", auth=_AUTH)
    assert callable(app)


def test_http_app_propagates_bad_auth():
    with pytest.raises(ValueError):
        mk_http_app(["os.path:basename"], name="conn", auth={"type": "nope"})


# --- CLI --http wiring (no port bind) ----------------------------------------


def test_cli_http_passes_auth_host_port(tmp_path, monkeypatch):
    from py2mcp import http as http_mod
    from py2mcp.serve import main

    cfg = tmp_path / "c.json"
    cfg.write_text(
        json.dumps({"name": "Conn", "refs": ["os.path:basename"], "auth": _AUTH, "port": 9001})
    )
    captured = {}

    def fake_serve_http(refs, **kwargs):
        captured["refs"] = list(refs)
        captured.update(kwargs)

    monkeypatch.setattr(http_mod, "serve_http", fake_serve_http)
    main(["--http", "--config", str(cfg)])
    assert captured["refs"] == ["os.path:basename"]
    assert captured["name"] == "Conn"
    assert captured["auth"] == _AUTH
    assert captured["port"] == 9001
    assert captured["host"] == "127.0.0.1"
