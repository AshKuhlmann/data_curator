import pytest
from unittest.mock import patch
from data_curator_app import cli


@pytest.fixture
def mock_core():
    """Fixture to mock the core module imported by cli.py."""
    with patch("data_curator_app.cli.core", autospec=True) as mock:
        yield mock


def test_scan_wrapper(mock_core):
    """Test the scan wrapper function."""
    cli.scan("/tmp/repo", "filter")
    mock_core.scan_directory.assert_called_once_with("/tmp/repo", "filter")


def test_set_status_wrapper(mock_core):
    """Test the set_status wrapper function."""
    cli.set_status("file.txt", "keep_forever")
    mock_core.update_file_status.assert_called_once_with("file.txt", "keep_forever")


def test_manage_tags_wrapper(mock_core):
    """Test the manage_tags wrapper function."""
    cli.manage_tags("file.txt", tags_to_add=["a"], tags_to_remove=["b"])
    mock_core.manage_tags.assert_called_once_with(
        "file.txt", tags_to_add=["a"], tags_to_remove=["b"]
    )


def test_rename_wrapper(mock_core):
    """Test the rename wrapper function."""
    cli.rename("/tmp/repo", "old.txt", "new.txt")
    mock_core.rename_file.assert_called_once_with("/tmp/repo/old.txt", "new.txt")


def test_delete_wrapper(mock_core):
    """Test the delete wrapper function."""
    cli.delete("/tmp/repo", "file.txt")
    mock_core.delete_file.assert_called_once_with("/tmp/repo/file.txt")


def test_get_expired_wrapper(mock_core):
    """Test the get_expired wrapper function."""
    cli.get_expired()
    mock_core.check_for_expired_files.assert_called_once()


@patch("data_curator_app.cli.scan")
def test_main_scan_command(mock_scan, monkeypatch, capsys):
    """Test that the main function calls the scan wrapper."""
    monkeypatch.setattr("sys.argv", ["cli.py", "/tmp/repo", "scan", "--filter", "term"])
    mock_scan.return_value = ["file1.txt"]

    cli.main()

    mock_scan.assert_called_once_with("/tmp/repo", "term")
    captured = capsys.readouterr()
    assert "Files available for review:" in captured.out
    assert "file1.txt" in captured.out
