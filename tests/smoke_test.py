"""Smoke tests before publishing to verify the wheel and source distribution."""

from __future__ import annotations

import subprocess
import sys

import ideagraph


def test_basic_import() -> None:
    """Test basic import."""
    print(f"Python version: {sys.version}")
    print(f"Package version: {ideagraph.__version__}")

    # Ensure it's not importing the local folder
    if "site-packages" not in ideagraph.__file__ and "dist" not in ideagraph.__file__:
        print(f"Warning: Package imported from unexpected location: {ideagraph.__file__}")


def test_cli_help() -> None:
    """Test CLI help."""
    # Ensure the 'ideagraph' entry point is installed and runs
    result = subprocess.run(["ideagraph", "--help"], capture_output=True, text=True, check=False)  # noqa: S607
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower()


if __name__ == "__main__":
    test_basic_import()
    print("Smoke test passed: Package is importable.")

    test_cli_help()
    print("Smoke test passed: The CLI is executable.")
