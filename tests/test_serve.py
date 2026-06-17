"""Tests for the stdio serve runner's pure config-resolution helpers.

The blocking ``serve_stdio`` (which runs a live server) is not exercised here;
the unit-testable surface is ``resolve_server_config`` / ``load_server_config``.
"""

import json

import pytest

from py2mcp.serve import load_server_config, resolve_server_config


def test_resolve_explicit_refs():
    refs, name = resolve_server_config(refs=["os.path:basename"], name="Paths")
    assert refs == ["os.path:basename"]
    assert name == "Paths"


def test_resolve_default_name():
    refs, name = resolve_server_config(refs=["a:b"])
    assert refs == ["a:b"]
    assert name == "py2mcp Server"


def test_resolve_from_config(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"name": "Cfg", "refs": ["a:b"]}))
    refs, name = resolve_server_config(config=str(cfg))
    assert refs == ["a:b"]
    assert name == "Cfg"


def test_config_refs_then_cli_refs_and_name_override(tmp_path):
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"name": "Cfg", "refs": ["a:b"]}))
    refs, name = resolve_server_config(config=str(cfg), refs=["c:d"], name="Override")
    assert refs == ["a:b", "c:d"]
    assert name == "Override"


def test_no_refs_raises():
    with pytest.raises(ValueError):
        resolve_server_config()


def test_load_bad_config_raises(tmp_path):
    cfg = tmp_path / "bad.json"
    cfg.write_text(json.dumps({"name": "x"}))  # missing the 'refs' list
    with pytest.raises(ValueError):
        load_server_config(str(cfg))


def test_main_missing_config_is_clean_error():
    # a missing/unreadable bundled config must exit cleanly (argparse error),
    # not dump a raw OSError traceback (the .mcpb launches this command).
    from py2mcp.serve import main

    with pytest.raises(SystemExit):
        main(["--config", "/nonexistent/py2mcp_config.json"])
