"""Shared helpers for parsing CLI options."""

from __future__ import annotations

import json
from typing import Any

import typer


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
