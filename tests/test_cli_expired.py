import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def write_state(repo: Path, state: dict) -> None:
    (repo / ".curator_state.json").write_text(json.dumps(state))


def test_expired_json_includes_details(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # Create a file and expired state entry
    (repo / "old.txt").write_text("x")
    state = {
        "old.txt": {
            "status": "keep",
            "keep_days": 90,
            # Clearly in the past
            "expiry_date": "2000-01-01T00:00:00",
        }
    }
    write_state(repo, state)

    res = run_cli(str(repo), ["expired", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert "expired" in data and "details" in data
    assert data["expired"] == ["old.txt"]
    assert len(data["details"]) == 1
    d0 = data["details"][0]
    assert d0["filename"] == "old.txt"
    assert d0["status"] == "keep"
    assert "keep_days" in d0 and isinstance(d0["keep_days"], int)
    assert d0["expired"] is True
    assert "days_overdue" in d0 and isinstance(d0["days_overdue"], int)


def test_mark_decide_later_idempotent(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "old.txt").write_text("x")
    state = {
        "old.txt": {
            "status": "keep",
            "keep_days": 90,
            "expiry_date": "2000-01-01T00:00:00",
        }
    }
    write_state(repo, state)

    # First mark should update the file
    r1 = run_cli(str(repo), ["expired", "--mark-decide-later", "--json"])
    assert r1.returncode == 0, r1.stderr
    j1 = json.loads(r1.stdout)
    assert "updated" in j1 and j1["updated"] == ["old.txt"]

    # Second mark should find nothing to update
    r2 = run_cli(str(repo), ["expired", "--mark-decide-later", "--json"])
    assert r2.returncode == 0, r2.stderr
    j2 = json.loads(r2.stdout)
    assert j2["updated"] == []
