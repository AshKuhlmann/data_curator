import json
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from data_curator_app import rules_engine as engine


@pytest.fixture
def rules_file(tmp_path):
    """A fixture to create a temporary rules file for testing."""
    rules = [
        {
            "name": "Delete old logs",
            "conditions": [
                {"field": "extension", "operator": "is", "value": ".log"},
                {"field": "age_days", "operator": "gt", "value": 30},
            ],
            "action": "delete",
        },
        {
            "name": "Tag screenshots",
            "conditions": [
                {"field": "filename", "operator": "startswith", "value": "Screenshot"}
            ],
            "action": "add_tag",
            "action_value": "screenshot",
        },
        {
            "name": "Tag all text files",
            "conditions": [{"field": "extension", "operator": "is", "value": ".txt"}],
            "action": "add_tag",
            "action_value": "text",
        },
    ]
    file_path = tmp_path / engine.RULES_FILENAME
    file_path.write_text(json.dumps(rules))
    return str(file_path)


def test_load_rules_success(rules_file):
    """Test that rules are loaded correctly from a valid JSON file."""
    rules = engine.load_rules(rules_file)
    assert len(rules) == 3
    assert rules[0]["name"] == "Delete old logs"


def test_load_rules_file_not_found():
    """Test that loading rules from a non-existent file returns an empty list."""
    assert engine.load_rules("non_existent_file.json") == []


def test_load_rules_corrupted_file(tmp_path):
    """Test that a corrupted JSON file results in an empty list of rules."""
    corrupted_file = tmp_path / "corrupted.json"
    corrupted_file.write_text("{'invalid_json':}")
    assert engine.load_rules(str(corrupted_file)) == []


def test_evaluate_condition_operators():
    """Test the various condition operators with different values."""
    # String operators
    assert engine._evaluate_condition("test.txt", "is", "test.txt")
    assert not engine._evaluate_condition("test.txt", "is", "other.txt")
    assert engine._evaluate_condition("test.txt", "contains", "st.t")
    assert not engine._evaluate_condition("test.txt", "contains", "st.f")
    assert engine._evaluate_condition("test.txt", "startswith", "test")
    assert not engine._evaluate_condition("test.txt", "startswith", "other")
    assert engine._evaluate_condition("test.txt", "endswith", ".txt")
    assert not engine._evaluate_condition("test.txt", "endswith", ".log")

    # Numerical operators
    assert engine._evaluate_condition(30, "gt", 20)
    assert not engine._evaluate_condition(30, "gt", 40)
    assert engine._evaluate_condition(20, "lt", 30)
    assert not engine._evaluate_condition(40, "lt", 30)

    # Type mismatch should fail gracefully
    assert not engine._evaluate_condition("abc", "gt", 10)


def test_get_file_attribute(tmp_path):
    """Test retrieving different attributes from a file."""
    test_file = tmp_path / "file.TXT"  # Uppercase to test normalization
    test_file.write_text("data")

    # Test extension (should be lowercased)
    ext = engine._get_file_attribute("extension", "file.TXT", str(test_file))
    assert ext == ".txt"

    # Test filename
    name = engine._get_file_attribute("filename", "file.TXT", str(test_file))
    assert name == "file.TXT"

    # Test age
    age = engine._get_file_attribute("age_days", "file.TXT", str(test_file))
    assert age == 0

    # Test unsupported attribute
    assert engine._get_file_attribute("unsupported", "file.txt", str(test_file)) is None


def test_evaluate_file_matches_rule(tmp_path, rules_file):
    """Test that a file is correctly matched against a rule."""
    # Create a file that matches the "Tag screenshots" rule
    screenshot_file = tmp_path / "Screenshot-2024.png"
    screenshot_file.touch()

    rules = engine.load_rules(rules_file)
    result = engine.evaluate_file("Screenshot-2024.png", str(screenshot_file), rules)

    assert result is not None
    assert result["action"] == "add_tag"
    assert result["action_value"] == "screenshot"


def test_evaluate_file_no_match(tmp_path, rules_file):
    """Test that a file with no matching rules returns None."""
    other_file = tmp_path / "document.pdf"
    other_file.touch()

    rules = engine.load_rules(rules_file)
    result = engine.evaluate_file("document.pdf", str(other_file), rules)
    assert result is None


def test_evaluate_file_multiple_conditions(tmp_path, rules_file):
    """Test a rule with multiple conditions that are all met."""
    # Create a log file older than 30 days
    log_file = tmp_path / "old.log"
    log_file.touch()
    # Mock the modification time to be in the past
    past_time = (datetime.now() - timedelta(days=35)).timestamp()
    with patch("os.path.getmtime", return_value=past_time):
        rules = engine.load_rules(rules_file)
        result = engine.evaluate_file("old.log", str(log_file), rules)

    assert result is not None
    assert result["action"] == "delete"


def test_evaluate_file_first_match_wins(tmp_path, rules_file):
    """Test that the first matching rule in the list is returned."""
    # This file matches both "Tag screenshots" and "Tag all text files" (if it was .txt)
    # Let's make a .txt file that starts with Screenshot
    screenshot_txt_file = tmp_path / "Screenshot.txt"
    screenshot_txt_file.touch()

    rules = engine.load_rules(rules_file)
    result = engine.evaluate_file("Screenshot.txt", str(screenshot_txt_file), rules)

    # "Tag screenshots" comes before "Tag all text files", so it should be the match
    assert result is not None
    assert result["name"] == "Tag screenshots"
    assert result["action_value"] == "screenshot"
