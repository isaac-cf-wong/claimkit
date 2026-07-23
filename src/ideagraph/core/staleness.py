"""Content-digest helpers for detecting when an artefact has changed.

These are model-agnostic: they turn bytes or a file into a stable, prefixed
digest string. Detecting whether a graph node's evidence has drifted (comparing
a recorded digest against a freshly computed one) lives in the research-profile
semantics (:mod:`ideagraph.kg.profiles.research_ops`).
"""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_digest(data: bytes, *, algorithm: str = "sha256") -> str:
    """Compute a prefixed content digest of ``data``.

    Args:
        data: The bytes to hash.
        algorithm: A hash algorithm name understood by :mod:`hashlib`.

    Returns:
        The digest as ``"<algorithm>:<hexdigest>"``, e.g. ``"sha256:ab12..."``.
        The prefix keeps the algorithm attached to the value so a later
        comparison cannot silently mix algorithms.

    """
    digest = hashlib.new(algorithm, data).hexdigest()
    return f"{algorithm}:{digest}"


def hash_file(path: str | Path, *, algorithm: str = "sha256") -> str:
    """Compute the prefixed content digest of a file.

    Args:
        path: Path to the file to hash.
        algorithm: A hash algorithm name understood by :mod:`hashlib`.

    Returns:
        The digest as ``"<algorithm>:<hexdigest>"``.

    """
    return compute_digest(Path(path).read_bytes(), algorithm=algorithm)
