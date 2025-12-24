"""Logging utilities."""

import traceback
from pathlib import Path


def log_error(msg: str, exc: Exception | None = None):
    """Log errors to a file for debugging."""
    log_file = Path.home() / "vidfetch_error.log"
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"{msg}\n")
            if exc:
                f.write(f"{traceback.format_exc()}\n")
            f.write("-" * 50 + "\n")
    except Exception:
        pass  # Can't log if logging fails

