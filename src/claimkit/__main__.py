"""Main entry point for the claimkit package."""

from __future__ import annotations

if __name__ == "__main__":
    from claimkit.utils.log import setup_logger

    setup_logger(print_version=True)
