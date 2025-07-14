import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from data_curator_app import curator_core as core


def test_load_state_nonexistent(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))
    assert core.load_state() == {}


def test_save_and_load_state(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))
    data = {"file.txt": {"status": "keep_forever"}}
    core.save_state(data)
    assert json.loads(state_file.read_text()) == data
    assert core.load_state() == data


def test_scan_directory_filters_processed(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))

    dir_path = tmp_path / "repo"
    dir_path.mkdir()
    for name in ["a.txt", "b.txt", "c.txt"]:
        (dir_path / name).write_text("data")

    state = {
        "a.txt": {"status": "keep_forever"},
        "b.txt": {"status": "decide_later"},
    }
    core.save_state(state)

    files = core.scan_directory(dir_path)
    assert sorted(files) == ["b.txt", "c.txt"]


def test_manage_tags_add_remove(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))

    tags = core.manage_tags("file.txt", tags_to_add=["one", "two"])
    assert sorted(tags) == ["one", "two"]

    tags = core.manage_tags("file.txt", tags_to_add=["two", "three"])
    assert sorted(tags) == ["one", "three", "two"]

    tags = core.manage_tags("file.txt", tags_to_remove=["one"])
    assert sorted(tags) == ["three", "two"]


def test_scan_directory_filter_by_tag(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))

    dir_path = tmp_path / "repo"
    dir_path.mkdir()
    for name in ["a.txt", "b.txt", "c.txt"]:
        (dir_path / name).write_text("data")

    core.manage_tags("b.txt", tags_to_add=["tag1"])
    result = core.scan_directory(dir_path, "tag1")
    assert result == ["b.txt"]


def test_update_file_status_and_expiry(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))

    core.update_file_status("test.txt", "keep_90_days")
    state = core.load_state()
    assert state["test.txt"]["status"] == "keep_90_days"
    expiry = datetime.fromisoformat(state["test.txt"]["expiry_date"])
    assert expiry - datetime.now() > timedelta(days=89)


def test_rename_file_updates_state(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))
    file_path = tmp_path / "old.txt"
    file_path.write_text("data")
    assert core.rename_file(str(file_path), "new.txt")
    new_path = tmp_path / "new.txt"
    assert new_path.exists()
    state = core.load_state()
    assert "new.txt" in state and state["new.txt"]["status"] == "renamed"


def test_rename_file_existing(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))
    (tmp_path / "old.txt").write_text("data")
    (tmp_path / "new.txt").write_text("data")
    assert not core.rename_file(str(tmp_path / "old.txt"), "new.txt")
    assert (tmp_path / "old.txt").exists()


def test_delete_file(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))
    file_path = tmp_path / "del.txt"
    file_path.write_text("x")
    assert core.delete_file(str(file_path))
    assert not file_path.exists()
    state = core.load_state()
    assert state["del.txt"]["status"] == "deleted"


def test_check_for_expired_files(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    monkeypatch.setattr(core, "STATE_FILE", str(state_file))
    past = datetime.now() - timedelta(days=1)
    future = datetime.now() + timedelta(days=1)
    state = {
        "old.txt": {"status": "keep_90_days", "expiry_date": past.isoformat()},
        "new.txt": {"status": "keep_90_days", "expiry_date": future.isoformat()},
        "other.txt": {"status": "keep_forever"},
    }
    core.save_state(state)
    expired = core.check_for_expired_files()
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
    monkeypatch.setattr(core.os, "system", lambda cmd: called.setdefault("cmd", cmd))

    core.open_file_location(str(file_path))
    assert called["cmd"].startswith("open ")
    assert str(dir_path) in called["cmd"]


def test_open_file_location_linux(tmp_path, monkeypatch):
    dir_path = tmp_path / "folder"
    dir_path.mkdir()
    file_path = dir_path / "file.txt"
    file_path.write_text("x")

    monkeypatch.setattr(core.os, "name", "posix", raising=False)
    monkeypatch.setattr(core.os, "uname", lambda: SimpleNamespace(sysname="Linux"))
    called = {}
    monkeypatch.setattr(core.os, "system", lambda cmd: called.setdefault("cmd", cmd))

    core.open_file_location(str(file_path))
    assert called["cmd"].startswith("xdg-open ")
    assert str(dir_path) in called["cmd"]
