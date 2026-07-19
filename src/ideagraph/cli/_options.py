"""Shared helpers for parsing CLI options."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

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


def parse_meta_json(items: list[str] | None) -> dict[str, Any]:
    """Parse repeatable ``KEY=JSON`` options into a dict of decoded values.

    Lets metadata hold structured (nested / numeric / list) values that the
    flat string form of :func:`parse_meta` cannot express.

    Args:
        items: The raw ``KEY=JSON`` strings, or None.

    Returns:
        A mapping of key to the JSON-decoded value (empty if ``items`` is falsy).

    Raises:
        typer.BadParameter: If an item is not ``KEY=JSON`` or the value is not
            valid JSON.
    """
    meta: dict[str, Any] = {}
    for item in items or []:
        key, sep, value = item.partition("=")
        if not sep or not key:
            raise typer.BadParameter(f"expected KEY=JSON, got {item!r}")
        try:
            meta[key] = json.loads(value)
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(f"invalid JSON for {key!r}: {exc}") from exc
    return meta


def merged_metadata(meta: list[str] | None, meta_json: list[str] | None) -> dict[str, Any]:
    """Combine ``--meta`` string entries and ``--meta-json`` structured entries.

    Args:
        meta: Raw ``KEY=VALUE`` strings, or None.
        meta_json: Raw ``KEY=JSON`` strings, or None.

    Returns:
        The merged metadata; JSON entries win on key collisions.
    """
    return {**parse_meta(meta), **parse_meta_json(meta_json)}
