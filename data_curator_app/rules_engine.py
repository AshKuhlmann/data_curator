"""Simple rules engine for automated curation tasks."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

RULES_FILE = "curator_rules.json"


def load_rules() -> List[Dict[str, Any]]:
    """Load rules from the project root JSON file."""
    if not os.path.exists(RULES_FILE):
        return []
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_field_value(field: str, filename: str, file_path: str) -> Any:
    if field == "extension":
        return os.path.splitext(filename)[1]
    if field == "filename":
        return filename
    if field == "age_days":
        mtime = os.path.getmtime(file_path)
        return (datetime.now() - datetime.fromtimestamp(mtime)).days
    return None


def _evaluate_condition(value: Any, operator: str, expected: Any) -> bool:
    if operator == "is":
        return value == expected
    if operator == "contains":
        return str(expected) in str(value)
    if operator == "gt":
        return float(value) > float(expected)
    if operator == "lt":
        return float(value) < float(expected)
    if operator == "startswith":
        return str(value).startswith(str(expected))
    if operator == "endswith":
        return str(value).endswith(str(expected))
    return False


def evaluate_file(
    filename: str, file_path: str, rules: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Return the matching rule action for a file if any."""
    for rule in rules:
        conditions_met = True
        for cond in rule.get("conditions", []):
            field_value = _get_field_value(cond.get("field"), filename, file_path)
            if field_value is None:
                conditions_met = False
                break
            if not _evaluate_condition(
                field_value, cond.get("operator"), cond.get("value")
            ):
                conditions_met = False
                break
        if conditions_met:
            return {
                "name": rule.get("name", ""),
                "action": rule.get("action"),
                "action_value": rule.get("action_value"),
            }
    return None
