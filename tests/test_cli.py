from unittest.mock import patch
import pytest
from data_curator_app import cli


@pytest.fixture
def mock_core():
    """Fixture to mock the core module imported by cli.py."""
    with patch("data_curator_app.cli.core", autospec=True) as mock:
        yield mock


@pytest.fixture
def mock_main_handlers():
    """Fixture to patch all handler functions called by main()."""
    with (
        patch("data_curator_app.cli.handle_scan", autospec=True) as m_scan,
        patch("data_curator_app.cli.handle_set_status", autospec=True) as m_status,
        patch("data_curator_app.cli.handle_manage_tags", autospec=True) as m_tags,
        patch("data_curator_app.cli.handle_rename", autospec=True) as m_rename,
        patch("data_curator_app.cli.handle_delete", autospec=True) as m_delete,
        patch("data_curator_app.cli.handle_get_expired", autospec=True) as m_expired,
        patch("data_curator_app.cli.handle_sort", autospec=True) as m_sort,
    ):
        yield {
            "scan": m_scan,
            "status": m_status,
            "tag": m_tags,
            "rename": m_rename,
            "delete": m_delete,
            "expired": m_expired,
            "sort": m_sort,
        }


def test_handle_scan_output_found(mock_core, capsys):
    """Test the console output of handle_scan when files are found."""
    mock_core.scan_directory.return_value = ["file1.txt", "file2.txt"]
    cli.handle_scan("/tmp/repo")
    captured = capsys.readouterr()
    assert "Files available for review:" in captured.out
    assert "  - file1.txt" in captured.out
    assert "  - file2.txt" in captured.out


def test_handle_scan_output_none(mock_core, capsys):
    """Test the console output of handle_scan when no files are found."""
    mock_core.scan_directory.return_value = []
    cli.handle_scan("/tmp/repo")
    captured = capsys.readouterr()
    assert "No files to review" in captured.out


def test_handle_get_expired_output_found(mock_core, capsys):
    """Test the console output of handle_get_expired when files are found."""
    mock_core.check_for_expired_files.return_value = ["expired.txt"]
    cli.handle_get_expired("/tmp/repo")
    captured = capsys.readouterr()
    assert "The following temporarily kept files have expired:" in captured.out
    assert "  - expired.txt" in captured.out


def test_handle_get_expired_output_none(mock_core, capsys):
    """Test the console output of handle_get_expired when no files are found."""
    mock_core.check_for_expired_files.return_value = []
    cli.handle_get_expired("/tmp/repo")
    captured = capsys.readouterr()
    assert "No temporarily kept files have expired." in captured.out


def test_main_scan_command(mock_main_handlers, monkeypatch):
    """Test that the main function correctly dispatches the scan command."""
    monkeypatch.setattr(
        "sys.argv",
        [
            "cli.py",
            "/tmp/repo",
            "scan",
            "--filter",
            "term",
            "--sort-by",
            "date",
            "--sort-order",
            "desc",
        ],
    )
    cli.main()
    mock_main_handlers["scan"].assert_called_once_with(
        "/tmp/repo", filter_term="term", sort_by="date", sort_order="desc"
    )


def test_main_sort_command(mock_main_handlers, monkeypatch):
    """Test that the main function correctly dispatches the sort command."""
    monkeypatch.setattr(
        "sys.argv", ["cli.py", "/tmp/repo", "sort", "size", "--order", "desc"]
    )
    cli.main()
    mock_main_handlers["sort"].assert_called_once_with(
        "/tmp/repo", sort_by="size", sort_order="desc"
    )


def test_main_status_command(mock_main_handlers, monkeypatch):
    """Test that the main function correctly dispatches the status command."""
    monkeypatch.setattr(
        "sys.argv",
        ["cli.py", "/tmp/repo", "status", "file.txt", "keep_forever"],
    )
    cli.main()
    mock_main_handlers["status"].assert_called_once_with(
        "/tmp/repo", "file.txt", "keep_forever"
    )


def test_main_tag_command(mock_main_handlers, monkeypatch):
    """Test that the main function correctly dispatches the tag command."""
    monkeypatch.setattr(
        "sys.argv",
        ["cli.py", "/tmp/repo", "tag", "file.txt", "--add", "a", "b", "--remove", "c"],
    )
    cli.main()
    mock_main_handlers["tag"].assert_called_once_with(
        "/tmp/repo", "file.txt", tags_to_add=["a", "b"], tags_to_remove=["c"]
    )


def test_main_rename_command(mock_main_handlers, monkeypatch):
    """Test that the main function correctly dispatches the rename command."""
    monkeypatch.setattr(
        "sys.argv", ["cli.py", "/tmp/repo", "rename", "old.txt", "new.txt"]
    )
    cli.main()
    mock_main_handlers["rename"].assert_called_once_with(
        "/tmp/repo", "old.txt", "new.txt"
    )


def test_main_delete_command(mock_main_handlers, monkeypatch):
    """Test that the main function correctly dispatches the delete command."""
    monkeypatch.setattr("sys.argv", ["cli.py", "/tmp/repo", "delete", "file.txt"])
    cli.main()
    mock_main_handlers["delete"].assert_called_once_with("/tmp/repo", "file.txt")


def test_main_expired_command(mock_main_handlers, monkeypatch):
    """Test that the main function correctly dispatches the expired command."""
    monkeypatch.setattr("sys.argv", ["cli.py", "/tmp/repo", "expired"])
    cli.main()
    mock_main_handlers["expired"].assert_called_once_with("/tmp/repo")
