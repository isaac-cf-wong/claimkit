"""Best-effort BibTeX parsing, for turning citation keys into readable labels.

Only what a provenance view needs — ``title`` / ``author`` / ``year`` per entry —
parsed tolerantly (nested braces in titles are common in exported ``.bib``
files); it is not a full BibTeX implementation.
"""

from __future__ import annotations

import re
from pathlib import Path

_TITLE_MAX = 80  # truncate long titles in the short citation label
_ENTRY_RE = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,", re.DOTALL)
_FIELD_RE = re.compile(r"(\w+)\s*=\s*", re.DOTALL)


def _read_value(text: str, start: int) -> tuple[str, int]:
    """Read a field value ({...}, "...", or bare) beginning at ``start``."""
    while start < len(text) and text[start] in " \t\n":
        start += 1
    if start >= len(text):
        return "", start
    ch = text[start]
    if ch == "{":
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start + 1 : i], i + 1
        return text[start + 1 :], len(text)
    if ch == '"':
        end = text.find('"', start + 1)
        end = len(text) if end < 0 else end
        return text[start + 1 : end], end + 1
    m = re.compile(r"[^,}\n]*").match(text, start)
    return (m.group(0).strip() if m else ""), (m.end() if m else start)


def _clean(value: str) -> str:
    """Strip braces/whitespace runs from a raw BibTeX value for display."""
    return re.sub(r"\s+", " ", value.replace("{", "").replace("}", "")).strip()


def parse_bibtex(path: str | Path) -> dict[str, dict[str, str]]:
    """Parse a ``.bib`` file into ``{key: {title, author, year}}`` (best effort).

    Args:
        path: Path to the BibTeX file (may not exist).

    Returns:
        A mapping of citation key to its title/author/year (each optional);
        empty if the file is absent.
    """
    path = Path(path)
    if not path.exists():
        return {}
    text = path.read_text(errors="replace")
    entries: dict[str, dict[str, str]] = {}
    for m in _ENTRY_RE.finditer(text):
        key = m.group(1)
        fields: dict[str, str] = {}
        i = m.end()
        depth = 1  # inside the entry's outer brace
        while i < len(text) and depth > 0:
            fm = _FIELD_RE.match(text, i)
            if fm:
                value, i = _read_value(text, fm.end())
                name = fm.group(1).lower()
                if name in ("title", "author", "year"):
                    fields[name] = _clean(value)
                continue
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        entries[key] = fields
    return entries


def format_citation(key: str, entry: dict[str, str] | None) -> str:
    """Render a short human label for a citation key, e.g. ``Author (2020) — Title``."""
    if not entry:
        return key
    author = entry.get("author", "").split(" and ")[0].split(",")[0].strip()
    year = entry.get("year", "")
    title = entry.get("title", "")
    head = " ".join(p for p in [author, f"({year})" if year else ""] if p).strip()
    if title:
        title = title if len(title) <= _TITLE_MAX else title[: _TITLE_MAX - 1] + "…"
        return f"{head} — {title}" if head else title
    return head or key
