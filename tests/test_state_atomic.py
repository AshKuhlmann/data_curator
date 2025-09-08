import json
import os
import sys
from pathlib import Path
from pathlib import Path as _Path

# Ensure local package is imported (not an already installed older version)
_ROOT = _Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from data_curator_app.curator_core import (
    STATE_FILENAME,
    load_state,
    save_state,
)  # noqa: E402


def read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_save_state_creates_and_rotates_backup(tmp_path: Path):
    repo = tmp_path
    state_path = repo / STATE_FILENAME
    bak_path = repo / f"{STATE_FILENAME}.bak"

    # Initial save should create only primary state (no backup yet)
    save_state(str(repo), {"a.txt": {"status": "decide_later"}})
    assert state_path.exists()
    assert not bak_path.exists()
    assert read_json(state_path) == {"a.txt": {"status": "decide_later"}}

    # Second save should rotate previous state into backup
    save_state(str(repo), {"a.txt": {"status": "keep_forever"}})
    assert state_path.exists()
    assert bak_path.exists()
    assert read_json(state_path) == {"a.txt": {"status": "keep_forever"}}
    assert read_json(bak_path) == {"a.txt": {"status": "decide_later"}}

    # Third save rotates backup again
    save_state(str(repo), {"b.txt": {"status": "decide_later"}})
    assert read_json(state_path) == {"b.txt": {"status": "decide_later"}}
    # Backup now contains the immediate previous state
    assert read_json(bak_path) == {"a.txt": {"status": "keep_forever"}}


def test_load_state_recovers_from_corrupt_primary_using_backup(tmp_path: Path):
    repo = tmp_path
    state_path = repo / STATE_FILENAME
    bak_path = repo / f"{STATE_FILENAME}.bak"

    # Create primary
    save_state(str(repo), {"v1.txt": {"status": "decide_later"}})
    # Rotate to create backup
    save_state(str(repo), {"v2.txt": {"status": "keep_forever"}})
    assert state_path.exists() and bak_path.exists()

    # Corrupt primary
    state_path.write_text("{ not: valid json }", encoding="utf-8")

    # load_state should fall back to backup
    recovered = load_state(str(repo))
    assert recovered == {"v1.txt": {"status": "decide_later"}}


def test_load_state_when_primary_missing_uses_backup(tmp_path: Path):
    repo = tmp_path
    state_path = repo / STATE_FILENAME
    bak_path = repo / f"{STATE_FILENAME}.bak"

    # Create a first state and rotate to produce a backup
    save_state(str(repo), {"first": {"status": "decide_later"}})
    save_state(str(repo), {"second": {"status": "keep_forever"}})
    assert state_path.exists() and bak_path.exists()

    # Remove primary (simulate crash between backup rotation and replace)
    os.remove(state_path)
    # load_state should return backup
    recovered = load_state(str(repo))
    assert recovered == {"first": {"status": "decide_later"}}


# ruff: noqa: E402
