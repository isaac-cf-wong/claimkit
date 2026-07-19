"""Deprecated import alias: ``claimkit`` was renamed to :mod:`ideagraph`.

Importing ``claimkit`` (or any ``claimkit.*`` submodule) transparently redirects
to the ``ideagraph`` package, so existing code keeps working. A
:class:`DeprecationWarning` is emitted once on first import. This alias is kept
for a release or two and will be removed; migrate imports to ``ideagraph``.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
import warnings

_OLD = "claimkit"
_NEW = "ideagraph"


class _AliasLoader(importlib.abc.Loader):
    """Load a ``claimkit[.x]`` name by returning the matching ``ideagraph`` module."""

    def __init__(self, target: str) -> None:
        self._target = target

    def create_module(self, spec):
        module = importlib.import_module(self._target)
        sys.modules[spec.name] = module
        return module

    def exec_module(self, module):
        return None


class _AliasFinder(importlib.abc.MetaPathFinder):
    """Redirect ``claimkit`` and ``claimkit.*`` imports to ``ideagraph``."""

    def find_spec(self, name, path=None, target=None):
        if name != _OLD and not name.startswith(_OLD + "."):
            return None
        redirected = _NEW + name[len(_OLD) :]
        return importlib.util.spec_from_loader(name, _AliasLoader(redirected))


# Install the finder ahead of the path-based finders so ``claimkit.core`` etc.
# resolve to ``ideagraph.core`` rather than this shim's (empty) package path.
if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _AliasFinder())

warnings.warn(
    "`claimkit` has been renamed to `ideagraph`; update your imports. "
    "The `claimkit` alias will be removed in a future release.",
    DeprecationWarning,
    stacklevel=2,
)

# Mirror the top-level public API so ``import claimkit; claimkit.Statement`` works.
_ideagraph = importlib.import_module(_NEW)
sys.modules[__name__].__dict__.update({k: v for k, v in _ideagraph.__dict__.items() if not k.startswith("__")})
__all__ = list(getattr(_ideagraph, "__all__", []))
