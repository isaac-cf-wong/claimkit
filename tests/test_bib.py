"""Tests for best-effort BibTeX parsing and citation formatting."""

from __future__ import annotations

from ideagraph.bib import format_citation, parse_bibtex

_BIB = r"""
@article{Chan2020,
  title = {Improving the background estimation technique with a {time-reversed} bank},
  author = {Chan, Man Leong and Cannon, Kipp and Others, A.},
  year = {2020},
  journal = {PRD},
}

@misc{plainkey,
  author = "Doe, Jane",
  year = "2021",
}
"""


def test_parse_bibtex(tmp_path):
    """parse_bibtex extracts title/author/year, tolerating nested braces.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    p = tmp_path / "refs.bib"
    p.write_text(_BIB)
    entries = parse_bibtex(p)
    assert set(entries) == {"Chan2020", "plainkey"}
    assert entries["Chan2020"]["title"].startswith("Improving the background")
    assert "time-reversed" in entries["Chan2020"]["title"]
    assert entries["Chan2020"]["year"] == "2020"
    assert entries["plainkey"]["author"] == "Doe, Jane"


def test_parse_bibtex_missing_file(tmp_path):
    """A missing .bib yields an empty mapping.

    Args:
        tmp_path: Pytest temporary directory fixture.

    """
    assert parse_bibtex(tmp_path / "nope.bib") == {}


def test_format_citation():
    """format_citation renders Author (Year) — Title, or falls back to the key."""
    entry = {"title": "A great paper", "author": "Chan, Man Leong and X, Y", "year": "2020"}
    out = format_citation("Chan2020", entry)
    assert "Chan" in out
    assert "(2020)" in out
    assert "A great paper" in out
    assert format_citation("bare", None) == "bare"
