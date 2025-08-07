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

    core.update_file_status(repo_path, "test.txt", "keep_90_days")
    state = core.load_state(repo_path)
    assert state["test.txt"]["status"] == "keep_90_days"
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
        "old.txt": {"status": "keep_90_days", "expiry_date": past.isoformat()},
        "new.txt": {"status": "keep_90_days", "expiry_date": future.isoformat()},
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
