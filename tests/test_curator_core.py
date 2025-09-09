import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from data_curator_app import curator_core as core


def test_load_state_nonexistent(tmp_path):
    assert core.load_state(str(tmp_path)) == {}


def test_save_and_load_state(tmp_path):
    repo_path = str(tmp_path)
    data = {"file.txt": {"status": "keep_forever"}}
    core.save_state(repo_path, data)
    state_file = tmp_path / core.STATE_FILENAME
    assert json.loads(state_file.read_text()) == data
    assert core.load_state(repo_path) == data


def test_scan_directory_filters_processed(tmp_path):
    dir_path = tmp_path / "repo"
    dir_path.mkdir()
    repo_path = str(dir_path)

    for name in ["a.txt", "b.txt", "c.txt"]:
        (dir_path / name).write_text("data")

    state = {
        "a.txt": {"status": "keep_forever"},
        "b.txt": {"status": "decide_later"},
    }
    core.save_state(repo_path, state)

    files = core.scan_directory(repo_path)
    assert sorted(files) == ["b.txt", "c.txt"]


def test_manage_tags_add_remove(tmp_path):
    repo_path = str(tmp_path)

    tags = core.manage_tags(repo_path, "file.txt", tags_to_add=["one", "two"])
    assert sorted(tags) == ["one", "two"]

    tags = core.manage_tags(repo_path, "file.txt", tags_to_add=["two", "three"])
    assert sorted(tags) == ["one", "three", "two"]

    tags = core.manage_tags(repo_path, "file.txt", tags_to_remove=["one"])
    assert sorted(tags) == ["three", "two"]


def test_scan_directory_filter_by_tag(tmp_path):
    dir_path = tmp_path / "repo"
    dir_path.mkdir()
    repo_path = str(dir_path)

    for name in ["a.txt", "b.txt", "c.txt"]:
        (dir_path / name).write_text("data")

    core.manage_tags(repo_path, "b.txt", tags_to_add=["tag1"])
    result = core.scan_directory(repo_path, "tag1")
    assert result == ["b.txt"]


def test_update_file_status_and_expiry(tmp_path):
    repo_path = str(tmp_path)

    core.update_file_status(repo_path, "test.txt", "keep", days=90)
    state = core.load_state(repo_path)
    assert state["test.txt"]["status"] == "keep"
    assert state["test.txt"]["keep_days"] == 90
    expiry = datetime.fromisoformat(state["test.txt"]["expiry_date"])
    assert expiry - datetime.now() > timedelta(days=89)


def test_rename_file_updates_state(tmp_path):
    repo_path = str(tmp_path)
    file_path = tmp_path / "old.txt"
    file_path.write_text("data")
    result = core.rename_file(str(file_path), "new.txt")
    new_path = tmp_path / "new.txt"
    assert new_path.exists()
    state = core.load_state(repo_path)
    assert "new.txt" in state and state["new.txt"]["status"] == "renamed"
    assert result is not None
    assert result["action"] == "rename"
    assert result["old_path"] == str(file_path)
    assert result["new_path"] == str(new_path)


def test_rename_file_existing(tmp_path):
    (tmp_path / "old.txt").write_text("data")
    (tmp_path / "new.txt").write_text("data")
    assert core.rename_file(str(tmp_path / "old.txt"), "new.txt") is None
    assert (tmp_path / "old.txt").exists()


def test_delete_file_moves_to_trash(tmp_path):
    repo_path = str(tmp_path)
    file_path = tmp_path / "del.txt"
    file_path.write_text("x")

    result = core.delete_file(str(file_path))

    trash_path = tmp_path / core.TRASH_DIR_NAME / "del.txt"
    assert not file_path.exists()
    assert trash_path.exists()

    state = core.load_state(repo_path)
    assert state["del.txt"]["status"] == "deleted"

    assert result is not None
    assert result["action"] == "delete"
    assert result["original_path"] == str(file_path)
    assert result["new_path"] == str(trash_path)


def test_undo_delete(tmp_path):
    repo_path = str(tmp_path)
    file_path = tmp_path / "del.txt"
    file_path.write_text("x")

    last_action = core.delete_file(str(file_path))
    assert last_action is not None
    assert not file_path.exists()

    assert core.undo_delete(last_action)
    assert file_path.exists()

    state = core.load_state(repo_path)
    assert state["del.txt"]["status"] == "decide_later"


def test_undo_rename(tmp_path):
    repo_path = str(tmp_path)
    file_path = tmp_path / "old.txt"
    file_path.write_text("data")

    # Rename old.txt -> new.txt
    last_action = core.rename_file(str(file_path), "new.txt")
    assert last_action is not None
    new_path = tmp_path / "new.txt"
    assert new_path.exists()
    assert not file_path.exists()

    # Undo the rename: new.txt -> old.txt
    undo_action = {
        "action": "rename",
        "old_path": str(new_path),
        "new_path": str(file_path),
    }
    core.rename_file(undo_action["old_path"], "old.txt")
    assert file_path.exists()
    assert not new_path.exists()

    # Check state
    state = core.load_state(repo_path)
    assert "old.txt" in state
    assert state["old.txt"]["status"] == "renamed"


def test_check_for_expired_files(tmp_path):
    repo_path = str(tmp_path)
    past = datetime.now() - timedelta(days=1)
    future = datetime.now() + timedelta(days=1)
    state = {
        "old.txt": {"status": "keep", "expiry_date": past.isoformat(), "keep_days": 30},
        "new.txt": {
            "status": "keep",
            "expiry_date": future.isoformat(),
            "keep_days": 30,
        },
        "other.txt": {"status": "keep_forever"},
    }
    core.save_state(repo_path, state)
    expired = core.check_for_expired_files(repo_path)
    assert expired == ["old.txt"]


def test_open_file_location_windows(tmp_path, monkeypatch):
    dir_path = tmp_path / "folder"
    dir_path.mkdir()
    file_path = dir_path / "file.txt"
    file_path.write_text("x")

    monkeypatch.setattr(core.os, "name", "nt", raising=False)
    called = {}

    def fake_startfile(path):
        called["path"] = path

    monkeypatch.setattr(core.os, "startfile", fake_startfile, raising=False)

    core.open_file_location(str(file_path))
    assert called["path"] == str(dir_path)


def test_open_file_location_macos(tmp_path, monkeypatch):
    dir_path = tmp_path / "folder"
    dir_path.mkdir()
    file_path = dir_path / "file.txt"
    file_path.write_text("x")

    monkeypatch.setattr(core.os, "name", "posix", raising=False)
    monkeypatch.setattr(core.os, "uname", lambda: SimpleNamespace(sysname="Darwin"))
    called = {}
    monkeypatch.setattr(
        core.subprocess, "run", lambda cmd, **kwargs: called.setdefault("cmd", cmd)
    )

    core.open_file_location(str(file_path))
    assert called["cmd"][0] == "open"
    assert called["cmd"][1] == str(dir_path)


def test_open_file_location_linux(tmp_path, monkeypatch):
    dir_path = tmp_path / "folder"
    dir_path.mkdir()
    file_path = dir_path / "file.txt"
    file_path.write_text("x")

    monkeypatch.setattr(core.os, "name", "posix", raising=False)
    monkeypatch.setattr(core.os, "uname", lambda: SimpleNamespace(sysname="Linux"))
    called = {}
    monkeypatch.setattr(
        core.subprocess, "run", lambda cmd, **kwargs: called.setdefault("cmd", cmd)
    )

    core.open_file_location(str(file_path))
    assert called["cmd"][0] == "xdg-open"
    assert called["cmd"][1] == str(dir_path)


def test_load_state_corrupted(tmp_path):
    """Test that a corrupted or invalid state file returns an empty dictionary."""
    repo_path = str(tmp_path)
    state_file = tmp_path / core.STATE_FILENAME
    state_file.write_text("this is not valid json")
    assert core.load_state(repo_path) == {}


def test_scan_directory_filter_case_insensitive(tmp_path):
    """Test that the scan directory filter is case-insensitive."""
    dir_path = tmp_path / "repo"
    dir_path.mkdir()
    repo_path = str(dir_path)

    (dir_path / "file_one.txt").write_text("data")
    (dir_path / "file_two.txt").write_text("data")

    # The filter 'ONE' should match 'file_one.txt'
    result = core.scan_directory(repo_path, "ONE")
    assert result == ["file_one.txt"]


def test_check_for_expired_files_invalid_date(tmp_path, capsys):
    """Test that an invalid date format in the state is handled gracefully."""
    repo_path = str(tmp_path)
    state = {
        "bad_date.txt": {
            "status": "keep",
            "keep_days": 10,
            "expiry_date": "not-a-valid-date",
        },
    }
    core.save_state(repo_path, state)
    expired = core.check_for_expired_files(repo_path)
    assert expired == []
    # Check that a warning was printed to stderr (or stdout)
    captured = capsys.readouterr()
    assert "Warning: Invalid date format" in captured.out


def test_rename_file_nonexistent(tmp_path):
    """Test that renaming a non-existent file fails and returns None."""
    non_existent_path = tmp_path / "non_existent.txt"
    result = core.rename_file(str(non_existent_path), "new.txt")
    assert result is None


def test_delete_file_nonexistent(tmp_path):
    """Test that deleting a non-existent file fails and returns None."""
    non_existent_path = tmp_path / "non_existent.txt"
    result = core.delete_file(str(non_existent_path))
    assert result is None


def test_scan_directory_ignores_subdirectories(tmp_path):
    """
    Test that scan_directory ignores subdirectories and only lists files.
    """
    repo_path = str(tmp_path)
    (tmp_path / "file1.txt").write_text("file 1")
    (tmp_path / "file2.txt").write_text("file 2")
    (tmp_path / "a_subdirectory").mkdir()

    # The scan should only find the two files, not the subdirectory.
    result = core.scan_directory(repo_path)
    assert sorted(result) == ["file1.txt", "file2.txt"]


def test_scan_directory_with_malformed_state_entry(tmp_path):
    """
    Test that scan_directory handles a malformed entry in the state file.
    If a file's metadata is not a dictionary, it should be treated as
    unprocessed and included in the scan results.
    """
    repo_path = str(tmp_path)
    (tmp_path / "file1.txt").write_text("file 1")
    (tmp_path / "file2.txt").write_text("file 2")

    # Create a state file with one valid entry and one malformed entry
    state = {
        "file1.txt": {"status": "keep_forever"},
        "file2.txt": "this-should-be-a-dictionary-but-is-not",
    }
    core.save_state(repo_path, state)

    # scan_directory should ignore file1.txt but include file2.txt because
    # its state is unrecognizable.
    result = core.scan_directory(repo_path)
    assert result == ["file2.txt"]


def test_scan_directory_sorting(tmp_path):
    """Test the sorting functionality of scan_directory."""
    repo_path = str(tmp_path)
    # Create files with different names, sizes, and modification times
    (tmp_path / "b.txt").write_text("medium")
    (tmp_path / "c.txt").write_text("long long text")
    (tmp_path / "a.txt").write_text("short")

    # --- Test sorting by name ---
    result = core.scan_directory(repo_path, sort_by="name", sort_order="asc")
    assert result == ["a.txt", "b.txt", "c.txt"]
    result = core.scan_directory(repo_path, sort_by="name", sort_order="desc")
    assert result == ["c.txt", "b.txt", "a.txt"]

    # --- Test sorting by size ---
    result = core.scan_directory(repo_path, sort_by="size", sort_order="asc")
    assert result == ["a.txt", "b.txt", "c.txt"]
    result = core.scan_directory(repo_path, sort_by="size", sort_order="desc")
    assert result == ["c.txt", "b.txt", "a.txt"]

    # --- Test sorting by date ---
    import os
    import time

    now = time.time()
    os.utime(str(tmp_path / "a.txt"), (now, now - 100))
    os.utime(str(tmp_path / "b.txt"), (now, now - 200))
    os.utime(str(tmp_path / "c.txt"), (now, now - 50))

    result = core.scan_directory(repo_path, sort_by="date", sort_order="asc")
    assert result == ["b.txt", "a.txt", "c.txt"]
    result = core.scan_directory(repo_path, sort_by="date", sort_order="desc")
    assert result == ["c.txt", "a.txt", "b.txt"]

    # --- Test default sorting (by name, asc) ---
    result = core.scan_directory(repo_path)
    assert result == ["a.txt", "b.txt", "c.txt"]


def test_scan_include_expired(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # Create files
    (repo / "old.txt").write_text("x")
    (repo / "new.txt").write_text("y")
    # Create state: old expired temporary keep, new unexpired keep
    from datetime import datetime, timedelta

    past = datetime.now() - timedelta(days=1)
    future = datetime.now() + timedelta(days=1)
    state = {
        "old.txt": {"status": "keep", "keep_days": 30, "expiry_date": past.isoformat()},
        "new.txt": {
            "status": "keep",
            "keep_days": 30,
            "expiry_date": future.isoformat(),
        },
    }
    core.save_state(str(repo), state)
    # Default scan excludes both (processed)
    files_default = core.scan_directory(str(repo), sort_by="name")
    assert files_default == []
    # With include_expired, include only the expired one
    files_with = core.scan_directory(str(repo), sort_by="name", include_expired=True)
    assert files_with == ["old.txt"]
