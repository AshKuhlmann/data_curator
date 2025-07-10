from __future__ import annotations

from pathlib import Path
from typing import List

from .config import load_config
from .curator_core import scan_directory


def sort_documents(config_path: str | Path | None = None) -> List[str]:
    """Load configuration and return sorted list of files to process."""
    config = load_config(config_path)
    files = scan_directory(config["documents_dir"])
    return sorted(f for f in files if f not in config["ignore_files"])


if __name__ == "__main__":
    import sys

    cfg = sys.argv[1] if len(sys.argv) > 1 else None
    for file in sort_documents(cfg):
        print(file)
