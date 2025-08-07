"""
A simple, file-based rules engine for automating curation tasks.

This module allows users to define a set of rules in a JSON file (`curator_rules.json`).
Each rule consists of conditions (e.g., file extension, age) and an action
(e.g., 'delete', 'tag'). The engine can then evaluate a file against these rules
and determine if an action should be taken, which can help automate the process
of tidying up a repository.

Example `curator_rules.json`:
[
    {
        "name": "Delete old logs",
        "conditions": [
            {"field": "extension", "operator": "is", "value": ".log"},
            {"field": "age_days", "operator": "gt", "value": 30}
        ],
        "action": "delete"
    },
    {
        "name": "Tag screenshots",
        "conditions": [
            {"field": "filename", "operator": "startswith", "value": "Screenshot"}
        ],
        "action": "add_tag",
        "action_value": "screenshot"
    }
]
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

# The name of the file where user-defined rules are stored.
RULES_FILENAME = "curator_rules.json"


def load_rules(rules_filepath: str = RULES_FILENAME) -> List[Dict[str, Any]]:
    """
    Loads curation rules from a JSON file.

    If the specified file doesn't exist, it returns an empty list, meaning
    no rules will be applied.

    Args:
        rules_filepath: The path to the JSON file containing the rules.
                        Defaults to RULES_FILENAME in the current directory.

    Returns:
        A list of rule dictionaries.
    """
    if not os.path.exists(rules_filepath):
        return []
    try:
        with open(rules_filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # In case of corruption or read errors, return no rules.
        return []


def _get_file_attribute(
    attribute_name: str, filename: str, file_path: str
) -> Optional[Any]:
    """
    Retrieves a specific attribute from a file for rule evaluation.

    This internal helper function acts as a dispatcher, fetching the correct
    piece of metadata or file property based on the `attribute_name`.

    Args:
        attribute_name: The name of the attribute to fetch (e.g., 'extension').
        filename: The name of the file.
        file_path: The full path to the file.

    Returns:
        The value of the requested attribute, or None if the attribute is
        not supported or found.
    """
    if attribute_name == "extension":
        return os.path.splitext(filename)[1].lower()
    if attribute_name == "filename":
        return filename
    if attribute_name == "age_days":
        try:
            modification_time = os.path.getmtime(file_path)
            age = datetime.now() - datetime.fromtimestamp(modification_time)
            return age.days
        except OSError:
            return None  # File might not exist or be accessible.
    return None


def _evaluate_condition(actual_value: Any, operator: str, expected_value: Any) -> bool:
    """
    Evaluates a single condition by comparing a file's attribute to an expected value.

    Args:
        actual_value: The actual value of the attribute from the file.
        operator: The comparison to perform (e.g., 'is', 'contains', 'gt').
        expected_value: The value to compare against, from the rule definition.

    Returns:
        True if the condition is met, False otherwise.
    """
    # Ensure consistent types for comparison where possible.
    str_actual = str(actual_value)
    str_expected = str(expected_value)

    if operator == "is":
        return str_actual == str_expected
    if operator == "contains":
        return str_expected in str_actual
    if operator == "startswith":
        return str_actual.startswith(str_expected)
    if operator == "endswith":
        return str_actual.endswith(str_expected)

    # For numerical comparisons, convert values to float.
    try:
        num_actual = float(actual_value)
        num_expected = float(expected_value)
        if operator == "gt":
            return num_actual > num_expected
        if operator == "lt":
            return num_actual < num_expected
    except (ValueError, TypeError):
        # If conversion fails, the condition cannot be met.
        return False

    return False


def evaluate_file(
    filename: str, file_path: str, rules: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """
    Evaluates a file against a list of rules and returns the first matching action.

    Rules are processed in the order they appear in the list. The first rule
    for which all conditions are met will be returned.

    Args:
        filename: The name of the file to evaluate.
        file_path: The full path to the file.
        rules: A list of rule dictionaries, loaded from `load_rules`.

    Returns:
        A dictionary representing the matched rule's action, or None if no
        rules were matched.
    """
    for rule in rules:
        all_conditions_met = True
        # A rule with no conditions is considered a match by default.
        for condition in rule.get("conditions", []):
            # Safely get condition properties.
            field = condition.get("field")
            operator = condition.get("operator")
            value = condition.get("value")

            if not all((field, operator, value is not None)):
                all_conditions_met = False
                break  # Invalid condition structure.

            file_attribute_value = _get_file_attribute(field, filename, file_path)

            if file_attribute_value is None:
                all_conditions_met = False
                break  # Could not retrieve the necessary file attribute.

            if not _evaluate_condition(file_attribute_value, operator, value):
                all_conditions_met = False
                break  # This specific condition was not met.

        if all_conditions_met:
            # Return the action part of the first rule that matches.
            return {
                "name": rule.get("name", "Unnamed Rule"),
                "action": rule.get("action"),
                "action_value": rule.get("action_value"),
            }
    return None  # No matching rules found.
