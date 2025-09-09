import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def make_repo(tmp_path: Path, n: int) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(n):
        (repo / f"f{i}.txt").write_text(str(i))
    return repo


def test_offset_beyond_end_returns_empty(tmp_path: Path):
    repo = make_repo(tmp_path, 5)
    res = run_cli(
        str(repo),
        [
            "scan",
            "--sort-by",
            "name",
            "--sort-order",
            "asc",
            "--offset",
            "999",
            "--json",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["files"] == []
    assert data["count"] == 0
    assert data["total"] == 5


def test_negative_offset_treated_as_zero(tmp_path: Path):
    repo = make_repo(tmp_path, 4)
    res = run_cli(
        str(repo),
        [
            "scan",
            "--sort-by",
            "name",
            "--sort-order",
            "asc",
            "--offset",
            "-10",
            "--json",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # Should behave like offset=0
    assert data["files"][0] == "f0.txt"
    assert data.get("offset", 0) == 0


def test_zero_limit_returns_empty_with_meta(tmp_path: Path):
    repo = make_repo(tmp_path, 3)
    res = run_cli(
        str(repo),
        [
            "scan",
            "--sort-by",
            "name",
            "--sort-order",
            "asc",
            "--limit",
            "0",
            "--json",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["files"] == []
    assert data["count"] == 0
    assert data["total"] == 3
    assert data["limit"] == 0


def test_negative_limit_means_unlimited(tmp_path: Path):
    repo = make_repo(tmp_path, 6)
    res = run_cli(
        str(repo),
        [
            "scan",
            "--sort-by",
            "name",
            "--sort-order",
            "asc",
            "--limit",
            "-5",
            "--json",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert len(data["files"]) == 6
    assert data["count"] == 6
    assert data["total"] == 6
