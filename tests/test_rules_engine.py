import os
import json
from datetime import datetime, timedelta
import pytest
from data_curator_app import rules_engine


# Fixture to create a temporary rules file
@pytest.fixture
def temp_rules_file(tmp_path):
    def _create_rules(rules_data):
        rules_file = tmp_path / "test_rules.json"
        with open(rules_file, "w") as f:
            json.dump(rules_data, f)
        return str(rules_file)

    return _create_rules


# Fixture to create a temporary file with a specific modification time
@pytest.fixture
def temp_file(tmp_path):
    def _create_file(name, mtime_days_ago=0):
        file_path = tmp_path / name
        file_path.write_text("content")
        mtime = (datetime.now() - timedelta(days=mtime_days_ago)).timestamp()
        os.utime(file_path, (mtime, mtime))
        return str(file_path)

    return _create_file


def test_load_rules_nonexistent(monkeypatch):
    """Ensure loading rules returns an empty list if the file doesn't exist."""
    monkeypatch.setattr(rules_engine, "RULES_FILE", "nonexistent.json")
    assert rules_engine.load_rules() == []


def test_load_rules_malformed_json(tmp_path, monkeypatch):
    """Ensure loading a malformed JSON file returns an empty list."""
    rules_file = tmp_path / "malformed.json"
    rules_file.write_text("[{'name': 'incomplete}")
    monkeypatch.setattr(rules_engine, "RULES_FILE", str(rules_file))
    with pytest.raises(json.JSONDecodeError):
        rules_engine.load_rules()


@pytest.mark.parametrize(
    "condition, filename, expected",
    [
        # Operator: is
        ({"field": "extension", "operator": "is", "value": ".log"}, "file.log", True),
        ({"field": "extension", "operator": "is", "value": ".txt"}, "file.log", False),
        # Operator: contains
        (
            {"field": "filename", "operator": "contains", "value": "screen"},
            "screenshot.png",
            True,
        ),
        (
            {"field": "filename", "operator": "contains", "value": "shot"},
            "screenshot.png",
            True,
        ),
        # Operator: startswith / endswith
        (
            {"field": "filename", "operator": "startswith", "value": "IMG"},
            "IMG_123.jpg",
            True,
        ),
        (
            {"field": "filename", "operator": "endswith", "value": ".tmp"},
            "data.tmp",
            True,
        ),
    ],
)
def test_evaluate_condition_string_operators(temp_file, condition, filename, expected):
    """Test various string-based operators in conditions."""
    file_path = temp_file(filename)
    rules = [{"name": "test rule", "conditions": [condition], "action": "test"}]
    result = rules_engine.evaluate_file(filename, file_path, rules)
    assert (result is not None) == expected


@pytest.mark.parametrize(
    "condition, age_days, expected",
    [
        # Operator: gt
        ({"field": "age_days", "operator": "gt", "value": 30}, 31, True),
        ({"field": "age_days", "operator": "gt", "value": 30}, 30, False),
        # Operator: lt
        ({"field": "age_days", "operator": "lt", "value": 10}, 9, True),
        ({"field": "age_days", "operator": "lt", "value": 10}, 10, False),
    ],
)
def test_evaluate_condition_numeric_operators(temp_file, condition, age_days, expected):
    """Test numeric operators like 'gt' and 'lt' for file age."""
    filename = "test.file"
    file_path = temp_file(filename, mtime_days_ago=age_days)
    rules = [{"name": "test age rule", "conditions": [condition], "action": "test"}]
    result = rules_engine.evaluate_file(filename, file_path, rules)
    assert (result is not None) == expected


def test_evaluate_file_multiple_conditions_all_met(temp_file):
    """Test a rule with multiple conditions that are all met (AND logic)."""
    filename = "archive.zip"
    file_path = temp_file(filename, mtime_days_ago=100)
    rules = [
        {
            "name": "Archive old zips",
            "conditions": [
                {"field": "extension", "operator": "is", "value": ".zip"},
                {"field": "age_days", "operator": "gt", "value": 90},
            ],
            "action": "archive",
        }
    ]
    result = rules_engine.evaluate_file(filename, file_path, rules)
    assert result is not None
    assert result["action"] == "archive"


def test_evaluate_file_multiple_conditions_one_not_met(temp_file):
    """Test a rule with multiple conditions where one is not met."""
    filename = "archive.zip"
    file_path = temp_file(filename, mtime_days_ago=50)
    rules = [
        {
            "name": "Archive old zips",
            "conditions": [
                {"field": "extension", "operator": "is", "value": ".zip"},
                {"field": "age_days", "operator": "gt", "value": 90},
            ],
            "action": "archive",
        }
    ]
    result = rules_engine.evaluate_file(filename, file_path, rules)
    assert result is None


def test_evaluate_file_no_matching_rule(temp_file):
    """Test that no action is returned if no rules match."""
    filename = "document.pdf"
    file_path = temp_file(filename)
    rules = [
        {
            "name": "Log rule",
            "conditions": [{"field": "extension", "operator": "is", "value": ".log"}],
            "action": "delete",
        }
    ]
    result = rules_engine.evaluate_file(filename, file_path, rules)
    assert result is None


def test_evaluate_file_returns_first_matching_rule(temp_file):
    """Ensure that the first rule that matches is the one that is returned."""
    filename = "important.log"
    file_path = temp_file(filename, mtime_days_ago=5)
    rules = [
        {
            "name": "Important logs",
            "conditions": [
                {"field": "filename", "operator": "contains", "value": "important"}
            ],
            "action": "tag_important",
        },
        {
            "name": "Generic logs",
            "conditions": [{"field": "extension", "operator": "is", "value": ".log"}],
            "action": "archive_log",
        },
    ]
    result = rules_engine.evaluate_file(filename, file_path, rules)
    assert result is not None
    assert result["action"] == "tag_important"
