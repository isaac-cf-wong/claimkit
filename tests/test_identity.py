"""Tests for global statement identity (article_id#node_id)."""

from __future__ import annotations

import pytest

from ideagraph import global_id, is_global_id, parse_global_id


def test_global_id_builds_and_parses():
    """A global id round-trips through build and parse."""
    gid = global_id("goncharov2022", "f3")
    assert gid == "goncharov2022#f3"
    assert parse_global_id(gid) == ("goncharov2022", "f3")


@pytest.mark.parametrize(("article", "node"), [("", "n1"), ("a#b", "n1"), ("a", ""), ("a", "n#1")])
def test_global_id_rejects_bad_components(article, node):
    """Empty or separator-containing components are rejected.

    Args:
        article: Candidate article id.
        node: Candidate node id.

    """
    with pytest.raises(ValueError, match="invalid"):
        global_id(article, node)


@pytest.mark.parametrize(
    ("value", "ok"), [("a#b", True), ("a#b#c", False), ("nohash", False), ("#b", False), ("a#", False)]
)
def test_is_global_id(value, ok):
    """is_global_id accepts exactly one separator with non-empty sides.

    Args:
        value: Candidate global id.
        ok: Expected validity.

    """
    assert is_global_id(value) is ok


def test_parse_global_id_raises_on_malformed():
    """parse_global_id raises ValueError on a malformed address."""
    with pytest.raises(ValueError, match="invalid global id"):
        parse_global_id("no-separator")
