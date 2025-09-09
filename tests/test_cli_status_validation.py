import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def test_status_invalid_rejected_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    res = run_cli(
        str(repo), ["status", "a.txt", "not_a_status", "--json"]
    )
    assert res.returncode == 3
    data = json.loads(res.stdout)
    assert data["code"] == 3 and "Invalid status" in data["error"]


def test_status_invalid_rejected_non_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    res = run_cli(
        str(repo), ["status", "a.txt", "not_a_status"]
    )
    assert res.returncode == 3
    assert res.stdout.strip().startswith("Error:")


def test_status_batch_invalid_rejected_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    res = run_cli(
        str(repo),
        [
            "status-batch",
            "--files",
            "a.txt",
            "--status",
            "not_a_status",
            "--json",
        ],
    )
    assert res.returncode == 3
    data = json.loads(res.stdout)
    assert data["code"] == 3 and "Invalid status" in data["error"]


def test_status_batch_invalid_rejected_non_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    res = run_cli(
        str(repo),
        [
            "status-batch",
            "--files",
            "a.txt",
            "--status",
            "not_a_status",
        ],
    )
    assert res.returncode == 3
    assert res.stdout.strip().startswith("Error:")

