"""Shared helpers for parsing CLI options."""

from __future__ import annotations

from datetime import datetime

import typer


def parse_datetime(value: str | None, flag: str) -> datetime | None:
    """Parse an ISO-8601 timestamp option, or None if not given.

    Args:
        value: The raw timestamp string, or None.
        flag: The option name, for error messages.

    Returns:
        The parsed :class:`datetime`, or None if ``value`` is None.

    Raises:
        typer.BadParameter: If ``value`` is not an ISO-8601 timestamp.
    """
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError as exc:
        raise typer.BadParameter(f"{flag}: not an ISO-8601 timestamp: {value!r}") from exc


def parse_meta(items: list[str] | None) -> dict[str, str]:
    """Parse repeatable ``KEY=VALUE`` options into a dict.

    Args:
        items: The raw ``KEY=VALUE`` strings, or None.

    Returns:
        A mapping of key to value (empty if ``items`` is falsy).

    Raises:
        typer.BadParameter: If an item is not of the form ``KEY=VALUE``.
    """
    meta: dict[str, str] = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise typer.BadParameter(f"expected KEY=VALUE, got {item!r}")
        meta[key] = value
    return meta
