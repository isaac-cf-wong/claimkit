"""Tests for the remote API client and the `ideagraph remote` CLI."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from ideagraph.cli.main import app
from ideagraph.remote import RemoteClient, RemoteConfig, RemoteError, load_config, save_config

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path, monkeypatch):
    """Point the CLI config at a temp file for every test.

    Args:
        tmp_path: Pytest temporary directory fixture.
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setenv("IDEAGRAPH_CONFIG", str(tmp_path / "config.toml"))


def test_config_roundtrip():
    """save_config then load_config preserves server and token."""
    save_config(RemoteConfig(server="http://x", token="tok"))
    cfg = load_config()
    assert cfg.server == "http://x"
    assert cfg.token == "tok"


def test_load_config_missing():
    """load_config returns None when no file exists."""
    assert load_config() is None


def test_request_rejects_non_http():
    """A non-http(s) server URL is rejected before any network call."""
    client = RemoteClient("ftp://x")
    with pytest.raises(RemoteError):
        client.list_graphs()


def _fake_request(recorder):
    """Build a fake _request that records calls and returns canned data.

    Args:
        recorder: A list to append (method, path, payload) tuples to.

    Returns:
        A function usable as RemoteClient._request.

    """

    def _request(self, method, path, payload=None):
        recorder.append((method, path, payload))
        if path == "/api/auth/token/":
            return {"token": "tok"}
        if path == "/api/graphs/" and method == "GET":
            return [{"slug": "g1", "title": "G1", "counts": {"nodes": 3, "edges": 2}}]
        if path.endswith("/content/"):
            return {"statements": [], "article_id": "a"}
        if path == "/api/graphs/" and method == "POST":
            return {"slug": payload["slug"]}
        return {"slug": "g1"}

    return _request


def test_push_creates_then_falls_back_to_replace(monkeypatch):
    """Push POSTs to create, and PUTs to replace on a 409 conflict."""
    calls: list = []

    def _request(self, method, path, payload=None):
        calls.append((method, path))
        if method == "POST":
            raise RemoteError("conflict", status=409)
        return {"slug": "g1"}

    monkeypatch.setattr(RemoteClient, "_request", _request)
    RemoteClient("http://x", "tok").push("g1", {"statements": []})
    assert calls == [("POST", "/api/graphs/"), ("PUT", "/api/graphs/g1/")]


def test_push_creates_when_absent(monkeypatch):
    """Push uses POST alone when the graph does not yet exist."""
    calls: list = []
    monkeypatch.setattr(RemoteClient, "_request", _fake_request(calls))
    RemoteClient("http://x", "tok").push("new", {"statements": []})
    assert calls == [("POST", "/api/graphs/", {"slug": "new", "content": {"statements": []}})]


def test_cli_login_saves_token(monkeypatch):
    """`remote login` stores the obtained token in the config."""
    monkeypatch.setattr(RemoteClient, "_request", _fake_request([]))
    result = runner.invoke(app, ["remote", "login", "http://x", "-u", "owner", "-p", "pw"])
    assert result.exit_code == 0
    assert load_config().token == "tok"


def test_cli_list(monkeypatch):
    """`remote list` prints each graph's slug."""
    save_config(RemoteConfig(server="http://x", token="tok"))
    monkeypatch.setattr(RemoteClient, "_request", _fake_request([]))
    result = runner.invoke(app, ["remote", "list"])
    assert result.exit_code == 0
    assert "g1" in result.stdout


def test_cli_list_requires_config():
    """`remote list` errors when not configured."""
    result = runner.invoke(app, ["remote", "list"])
    assert result.exit_code == 1
    assert "Not configured" in result.stderr


def test_cli_push_and_pull(monkeypatch, tmp_path):
    """`remote push` uploads a file and `remote pull` writes one back.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Pytest temporary directory fixture.
    """
    import json

    save_config(RemoteConfig(server="http://x", token="tok"))
    monkeypatch.setattr(RemoteClient, "_request", _fake_request([]))
    src = tmp_path / "g.json"
    src.write_text(json.dumps({"statements": [], "article_id": "a"}), encoding="utf-8")
    push = runner.invoke(app, ["remote", "push", "g1", str(src)])
    assert push.exit_code == 0
    out = tmp_path / "out.json"
    pull = runner.invoke(app, ["remote", "pull", "g1", str(out)])
    assert pull.exit_code == 0
    assert json.loads(out.read_text())["article_id"] == "a"


def test_cli_push_missing_file(monkeypatch, tmp_path):
    """`remote push` errors on a missing source file.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
        tmp_path: Pytest temporary directory fixture.
    """
    save_config(RemoteConfig(server="http://x", token="tok"))
    result = runner.invoke(app, ["remote", "push", "g1", str(tmp_path / "nope.json")])
    assert result.exit_code == 1
    assert "No such file" in result.stderr
