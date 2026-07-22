# ruff: noqa: PLC0415
"""The ``ideagraph remote`` command group: talk to a hosted server."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

remote_app = typer.Typer(help="Push, pull, and list graphs on a hosted ideagraph server.")


def _client(require_token: bool = True):
    """Build a RemoteClient from the saved config.

    Args:
        require_token: Whether a saved token is required.

    Returns:
        A configured RemoteClient.

    Raises:
        typer.Exit: If no config (or no token) is available.
    """
    from ideagraph.remote import RemoteClient, load_config

    config = load_config()
    if config is None or not config.server:
        typer.echo("Not configured. Run `ideagraph remote login <server>` first.", err=True)
        raise typer.Exit(code=1)
    if require_token and not config.token:
        typer.echo("Not authenticated. Run `ideagraph remote login <server>` first.", err=True)
        raise typer.Exit(code=1)
    return RemoteClient(config.server, config.token)


@remote_app.command("login")
def login_command(
    server: Annotated[str, typer.Argument(help="Base URL of the ideagraph server.")],
    username: Annotated[str, typer.Option("--username", "-u", prompt=True, help="Account username.")],
    password: Annotated[
        str,
        typer.Option("--password", "-p", prompt=True, hide_input=True, help="Account password."),
    ],
) -> None:
    """Authenticate to a server and save the token for later commands.

    Args:
        server: Base URL of the ideagraph server.
        username: Account username.
        password: Account password.
    """
    from ideagraph.remote import RemoteClient, RemoteConfig, RemoteError, save_config

    client = RemoteClient(server)
    try:
        token = client.obtain_token(username, password)
    except RemoteError as exc:
        typer.echo(f"Login failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    save_config(RemoteConfig(server=server, token=token))
    typer.echo(f"Logged in to {server}.")


@remote_app.command("list")
def list_command() -> None:
    """List the graphs you can see on the server."""
    from ideagraph.remote import RemoteError

    client = _client()
    try:
        graphs = client.list_graphs()
    except RemoteError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    if not graphs:
        typer.echo("No graphs.")
        return
    for graph in graphs:
        counts = graph.get("counts", {})
        typer.echo(f"{graph['slug']}\t{graph.get('title', '')}\t{counts.get('nodes', 0)} nodes")


@remote_app.command("push")
def push_command(
    slug: Annotated[str, typer.Argument(help="Slug to store the graph under.")],
    path: Annotated[Path, typer.Argument(help="Path to a graph JSON file.")],
) -> None:
    """Upload a local graph JSON file to the server (create or replace).

    Args:
        slug: Slug to store the graph under.
        path: Path to a graph JSON file.
    """
    import json

    from ideagraph.remote import RemoteError

    if not path.exists():
        typer.echo(f"No such file: {path}", err=True)
        raise typer.Exit(code=1)
    content = json.loads(path.read_text(encoding="utf-8"))
    client = _client()
    try:
        client.push(slug, content)
    except RemoteError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Pushed '{slug}'.")


@remote_app.command("pull")
def pull_command(
    slug: Annotated[str, typer.Argument(help="Slug of the graph to fetch.")],
    path: Annotated[Path | None, typer.Argument(help="Destination file (stdout if omitted).")] = None,
) -> None:
    """Download a graph from the server as JSON.

    Args:
        slug: Slug of the graph to fetch.
        path: Destination file, or stdout if omitted.
    """
    import json

    from ideagraph.remote import RemoteError

    client = _client(require_token=False)
    try:
        content = client.get_content(slug)
    except RemoteError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    text = json.dumps(content, indent=2, ensure_ascii=False)
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text + "\n", encoding="utf-8")
        typer.echo(f"Pulled '{slug}' to {path}.")
    else:
        typer.echo(text)
