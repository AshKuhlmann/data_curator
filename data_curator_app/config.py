from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml  # type: ignore

DEFAULT_CONFIG: Dict[str, Any] = {
    "documents_dir": ".",
    "ignore_files": [],
    "custom_rules": {},
}


def load_config(path: str | Path | None) -> Dict[str, Any]:
    """Load configuration from YAML file, falling back to defaults."""
    if path is None:
        return DEFAULT_CONFIG.copy()

    with open(path, "r") as f:
        data = yaml.safe_load(f) or {}

    return {
        "documents_dir": data.get("documents_dir") or DEFAULT_CONFIG["documents_dir"],
        "ignore_files": data.get("ignore_files")
        or list(DEFAULT_CONFIG["ignore_files"]),
        "custom_rules": data.get("custom_rules")
        or DEFAULT_CONFIG["custom_rules"].copy(),
    }
