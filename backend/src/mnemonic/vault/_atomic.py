"""Atomic file write helper. Used everywhere Mnemonic touches the vault."""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_text(path: Path, content: str) -> None:
    """Atomically write content to a file using a temporary file + rename.

    This ensures that if the write fails, the original file is not corrupted.

    Args:
        path: The file to write to.
        content: The content to write.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)
