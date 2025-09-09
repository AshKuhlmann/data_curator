import json
from pathlib import Path

from data_curator_app import curator_core as core


def test_save_injects_schema_version(tmp_path: Path):
    repo = tmp_path
    # Save minimal state
    core.save_state(str(repo), {})
    state_path = repo / core.STATE_FILENAME
    assert state_path.exists()
    data = json.loads(state_path.read_text())
    assert data.get("_schema_version") == 1
    # No other entries
    assert [k for k in data.keys() if k != "_schema_version"] == []


def test_update_overwrites_schema_version_to_current(tmp_path: Path):
    repo = tmp_path
    # Write a state with a bogus future version
    bogus = {"_schema_version": 999, "x.txt": {"status": "decide_later"}}
    (repo / core.STATE_FILENAME).write_text(json.dumps(bogus))

    # Perform an update which triggers save
    core.update_file_status(str(repo), "y.txt", "keep_forever")
    data = core.load_state(str(repo))
    assert data.get("_schema_version") == 1
    assert "x.txt" in data and "y.txt" in data


def test_expired_checks_ignore_schema_key(tmp_path: Path):
    repo = tmp_path
    # Manually craft a state including schema key and entries
    data = {
        "_schema_version": 1,
        "old.txt": {
            "status": "keep",
            "expiry_date": "2000-01-01T00:00:00",
            "keep_days": 30,
        },
        "new.txt": {"status": "keep_forever"},
    }
    (repo / core.STATE_FILENAME).write_text(json.dumps(data))
    # Functions should work without tripping on the schema key
    expired = core.check_for_expired_files(str(repo))
    assert expired == ["old.txt"]
    details = core.get_expired_details(str(repo))
    assert len(details) == 1 and details[0]["filename"] == "old.txt"
