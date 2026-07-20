"""Global statement identity across articles.

Within one article a statement is addressed by its bare ``node_id``. To point at
a statement in *another* article — the basis of cross-article edges — it is
addressed globally as ``article_id#node_id``. This module is the single source of
truth for that address format, so every layer (graph, CLI, library index) parses
and builds it the same way.

The separator is ``#`` and may not appear in either component; both components
must be non-empty. Keeping the rule in one place means a malformed address is
caught the same way everywhere rather than silently producing a dangling edge.
"""

from __future__ import annotations

#: Separator between the article id and the node id in a global address.
SEP = "#"

#: A global address has exactly two components: article id and node id.
_PARTS = 2


def global_id(article_id: str, node_id: str) -> str:
    """Build the global address ``article_id#node_id``.

    Args:
        article_id: The owning article's stable id.
        node_id: The statement's local id within that article.

    Returns:
        The global address.

    Raises:
        ValueError: If either component is empty or contains the separator.
    """
    if not article_id or SEP in article_id:
        raise ValueError(f"invalid article_id {article_id!r}: must be non-empty and not contain {SEP!r}")
    if not node_id or SEP in node_id:
        raise ValueError(f"invalid node_id {node_id!r}: must be non-empty and not contain {SEP!r}")
    return f"{article_id}{SEP}{node_id}"


def is_global_id(value: str) -> bool:
    """Return whether ``value`` is a well-formed ``article_id#node_id`` address.

    Args:
        value: The string to test.

    Returns:
        True if the string parses as a global address.
    """
    try:
        parse_global_id(value)
    except ValueError:
        return False
    return True


def parse_global_id(value: str) -> tuple[str, str]:
    """Split a global address into ``(article_id, node_id)``.

    Args:
        value: A ``article_id#node_id`` address.

    Returns:
        The ``(article_id, node_id)`` pair.

    Raises:
        ValueError: If ``value`` is not a well-formed global address (exactly one
            separator, both components non-empty).
    """
    parts = value.split(SEP)
    if len(parts) != _PARTS or not parts[0] or not parts[1]:
        raise ValueError(f"invalid global id {value!r}: expected 'article_id{SEP}node_id'")
    return parts[0], parts[1]
