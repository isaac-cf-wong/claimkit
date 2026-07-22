"""Client for a hosted ideagraph server's REST API.

Lets the local CLI push graphs to, pull graphs from, and list graphs on a hosted
ideagraph server (the Django + DRF app), authenticating with a token stored in a
small config file. Uses only the standard library so the core package gains no
new dependency.
"""

from __future__ import annotations

import json
import os
import tomllib
import urllib.error
import urllib.request
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any


class RemoteError(Exception):
    """A remote API call failed.

    Attributes:
        status: The HTTP status code, if the failure was an HTTP error.
    """

    def __init__(self, message: str, *, status: int | None = None) -> None:
        """Initialise the error.

        Args:
            message: A human-readable description.
            status: The HTTP status code, if any.
        """
        super().__init__(message)
        self.status = status


@dataclass
class RemoteConfig:
    """Saved connection details for a hosted server."""

    server: str
    token: str | None = None


def config_path() -> Path:
    """Return the path to the CLI config file.

    Honours ``IDEAGRAPH_CONFIG`` if set, else ``$XDG_CONFIG_HOME/ideagraph/
    config.toml``, else ``~/.config/ideagraph/config.toml``.

    Returns:
        The config file path.

    """
    override = os.environ.get("IDEAGRAPH_CONFIG")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "ideagraph" / "config.toml"


def load_config() -> RemoteConfig | None:
    """Load saved connection details, if any.

    Returns:
        The saved config, or ``None`` if no config file exists.

    """
    path = config_path()
    if not path.exists():
        return None
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return RemoteConfig(server=data.get("server", ""), token=data.get("token"))


def save_config(config: RemoteConfig) -> None:
    """Persist connection details to the config file.

    Args:
        config: The connection details to save.

    """
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f'server = "{config.server}"\n']
    if config.token:
        lines.append(f'token = "{config.token}"\n')
    path.write_text("".join(lines), encoding="utf-8")


class RemoteClient:
    """A thin client for the ideagraph server REST API."""

    def __init__(self, server: str, token: str | None = None) -> None:
        """Initialise the client.

        Args:
            server: Base URL of the server (e.g. ``https://ideagraph.example``).
            token: Optional auth token for authenticated requests.
        """
        self.server = server.rstrip("/")
        self.token = token

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        """Perform an HTTP request against the server and return parsed JSON.

        Args:
            method: HTTP method.
            path: Path under the server root (e.g. ``/api/graphs/``).
            payload: Optional JSON body.

        Returns:
            The parsed JSON response, or ``None`` for an empty body.

        Raises:
            RemoteError: On a non-2xx response or a connection failure.

        """
        if not self.server.startswith(("http://", "https://")):
            raise RemoteError(f"server must be an http(s) URL, got {self.server!r}")
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(self.server + path, data=data, method=method)  # noqa: S310 - scheme checked above
        request.add_header("Content-Type", "application/json")
        request.add_header("Accept", "application/json")
        if self.token:
            request.add_header("Authorization", f"Token {self.token}")
        try:
            with urllib.request.urlopen(request) as response:  # noqa: S310 - scheme checked above
                body = response.read().decode()
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise RemoteError(f"{exc.code} {exc.reason}: {detail}", status=exc.code) from exc
        except urllib.error.URLError as exc:
            raise RemoteError(f"could not reach {self.server}: {exc.reason}") from exc

    def obtain_token(self, username: str, password: str) -> str:
        """Exchange credentials for an auth token.

        Args:
            username: The account username.
            password: The account password.

        Returns:
            The issued token.

        Raises:
            RemoteError: If authentication fails.

        """
        result = self._request("POST", "/api/auth/token/", {"username": username, "password": password})
        return result["token"]

    def list_graphs(self) -> list[dict[str, Any]]:
        """List the graphs visible to the authenticated user.

        Returns:
            A list of graph metadata dicts.

        """
        return self._request("GET", "/api/graphs/")

    def get_content(self, slug: str) -> dict[str, Any]:
        """Fetch a graph's full serialised content.

        Args:
            slug: The graph slug.

        Returns:
            The serialised ProvenanceGraph dict.

        """
        return self._request("GET", f"/api/graphs/{slug}/content/")

    def push(self, slug: str, content: dict[str, Any]) -> dict[str, Any]:
        """Create the graph, or replace it if it already exists.

        Args:
            slug: The graph slug.
            content: The serialised ProvenanceGraph dict.

        Returns:
            The server's graph-metadata response.

        """
        try:
            return self._request("POST", "/api/graphs/", {"slug": slug, "content": content})
        except RemoteError as exc:
            if exc.status == HTTPStatus.CONFLICT:
                return self._request("PUT", f"/api/graphs/{slug}/", {"content": content})
            raise
