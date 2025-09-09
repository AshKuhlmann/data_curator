import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def test_status_batch_partial_failure_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "ok.txt").write_text("x")
    res = run_cli(
        str(repo),
        [
            "status-batch",
            "--files",
            "ok.txt",
            "missing.txt",
            "--status",
            "keep_forever",
            "--json",
        ],
    )
    assert res.returncode == 2  # any failure => code 2
    data = json.loads(res.stdout)
    assert data["updated"] == 1
    assert data["failed"] == 1
    assert len(data["results"]) == 2
    rmap = {r["filename"]: r for r in data["results"]}
    assert rmap["ok.txt"]["result"] == "updated"
    assert "error" in rmap["missing.txt"]


def test_tag_batch_success_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    (repo / "b.txt").write_text("b")
    res = run_cli(
        str(repo),
        ["tag-batch", "--files", "a.txt", "b.txt", "--add", "foo", "bar", "--json"],
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["updated"] == 2
    rmap = {r["filename"]: r for r in data["results"]}
    assert set(rmap["a.txt"]["tags"]) == {"foo", "bar"}
    assert set(rmap["b.txt"]["tags"]) == {"foo", "bar"}


def test_status_batch_from_file_and_stdin(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    (repo / "b.txt").write_text("b")

    # Write a file list
    filelist = tmp_path / "files.txt"
    filelist.write_text("a.txt\n")

    # From file
    p1 = run_cli(
        str(repo),
        [
            "status-batch",
            "--from-file",
            str(filelist),
            "--status",
            "keep_forever",
            "--json",
        ],
    )
    assert p1.returncode == 0, p1.stderr
    d1 = json.loads(p1.stdout)
    assert d1["updated"] == 1 and d1["failed"] == 0

    # From stdin
    cmd = [
        "python",
        "-m",
        "data_curator_app.cli",
        str(repo),
        "tag-batch",
        "--stdin",
        "--add",
        "x",
        "--json",
    ]
    p2 = subprocess.run(
        cmd,
        input="a.txt\nmissing_file_does_not_exist.txt\n",
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    # missing file should fail, a.txt should succeed
    assert p2.returncode == 2
    d2 = json.loads(p2.stdout)
    assert d2["updated"] == 1 and d2["failed"] == 1
    fnmap = {r["filename"]: r for r in d2["results"]}
    assert fnmap["a.txt"]["result"] == "updated"
    assert "error" in fnmap["missing_file_does_not_exist.txt"]

    # Error when no input sources
    p3 = run_cli(str(repo), ["status-batch", "--status", "decide_later", "--json"])
    assert p3.returncode == 3
    d3 = json.loads(p3.stdout)
    assert d3["code"] == 3 and "No filenames provided" in d3["error"]
