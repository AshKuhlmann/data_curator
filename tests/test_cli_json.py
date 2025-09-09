import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def test_status_json_success(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "f.txt").write_text("x")
    res = run_cli(str(repo), ["status", "f.txt", "keep_forever", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["result"] == "updated"
    assert data["filename"] == "f.txt"
    assert data["status"] == "keep_forever"


def test_status_json_missing_file_errors(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    res = run_cli(str(repo), ["status", "missing.txt", "keep_forever", "--json"])
    assert res.returncode == 2
    data = json.loads(res.stdout)
    assert data["error"].startswith("File 'missing.txt' not found")
    assert data["code"] == 2


def test_tag_json_add_remove(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "t.txt").write_text("t")
    res = run_cli(str(repo), ["tag", "t.txt", "--add", "one", "two", "--json"])
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["result"] == "updated"
    assert data["filename"] == "t.txt"
    assert set(data["tags"]) == {"one", "two"}

    res2 = run_cli(str(repo), ["tag", "t.txt", "--remove", "one", "--json"])
    assert res2.returncode == 0
    data2 = json.loads(res2.stdout)
    assert data2["result"] == "updated"
    assert set(data2["tags"]) == {"two"}


def test_rename_delete_restore_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "old.txt").write_text("o")

    # Rename
    r1 = run_cli(str(repo), ["rename", "old.txt", "new.txt", "--json"])
    assert r1.returncode == 0
    dj = json.loads(r1.stdout)
    assert dj["result"] == "renamed"
    assert dj["old"] == "old.txt" and dj["new"] == "new.txt"

    # Delete
    r2 = run_cli(str(repo), ["delete", "new.txt", "--yes", "--json"])
    assert r2.returncode == 0
    dd = json.loads(r2.stdout)
    assert dd["result"] == "deleted"
    assert dd["filename"] == "new.txt"
    assert dd["trash_path"].endswith("new.txt")

    # Restore
    r3 = run_cli(str(repo), ["restore", "new.txt", "--json"])
    assert r3.returncode == 0
    dr = json.loads(r3.stdout)
    assert dr["result"] == "restored"
    assert dr["filename"] == "new.txt"


def test_scan_limit_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(5):
        (repo / f"f{i}.txt").write_text(str(i))
    res = run_cli(
        str(repo),
        ["scan", "--sort-by", "name", "--sort-order", "asc", "--limit", "3", "--json"],
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    files = data["files"]
    assert len(files) == 3
    assert files == ["f0.txt", "f1.txt", "f2.txt"]


def test_status_keep_days_json_and_persist(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "keepme.txt").write_text("x")
    res = run_cli(str(repo), ["status", "keepme.txt", "keep", "--days", "30", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["result"] == "updated"
    assert data["status"] == "keep"
    assert data["days"] == 30
    # Verify state persisted
    st_path = repo / ".curator_state.json"
    st = json.loads(st_path.read_text())
    entry = st.get("keepme.txt", {})
    assert entry.get("status") == "keep"
    assert entry.get("keep_days") == 30
    assert "expiry_date" in entry
