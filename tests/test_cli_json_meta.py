import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def test_scan_json_includes_metadata_and_limit(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(5):
        (repo / f"f{i}.txt").write_text(str(i))
    res = run_cli(
        str(repo),
        ["scan", "--sort-by", "name", "--sort-order", "asc", "--limit", "3", "--json"],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["files"] == ["f0.txt", "f1.txt", "f2.txt"]
    assert data["count"] == 3
    assert data["total"] == 5
    assert data["limit"] == 3
    assert data["sort_by"] == "name"
    assert data["sort_order"] == "asc"
    assert data["recursive"] is False
    assert data.get("offset", 0) == 0


def test_sort_json_includes_metadata_and_limit(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(5):
        (repo / f"f{i}.txt").write_text(str(i))
    res = run_cli(
        str(repo), ["sort", "name", "--order", "desc", "--limit", "2", "--json"]
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["files"][:2] == ["f4.txt", "f3.txt"]
    assert data["count"] == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["sort_by"] == "name"
    assert data["sort_order"] == "desc"
    assert data["recursive"] is False
    assert data.get("offset", 0) == 0


def test_scan_offset_paging(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(6):
        (repo / f"f{i}.txt").write_text(str(i))
    res = run_cli(
        str(repo),
        [
            "scan",
            "--sort-by",
            "name",
            "--sort-order",
            "asc",
            "--offset",
            "2",
            "--limit",
            "2",
            "--json",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["files"] == ["f2.txt", "f3.txt"]
    assert data["count"] == 2
    assert data["total"] == 6
    assert data["offset"] == 2


def test_sort_offset_paging(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(6):
        (repo / f"f{i}.txt").write_text(str(i))
    res = run_cli(
        str(repo),
        ["sort", "name", "--order", "asc", "--offset", "4", "--limit", "5", "--json"],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["files"] == ["f4.txt", "f5.txt"]
    assert data["count"] == 2
    assert data["total"] == 6
    assert data["offset"] == 4


def test_scan_json_totals_filtered_vs_raw(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    for i in range(6):
        (repo / f"f{i}.txt").write_text(str(i))
    # Add a tag to one file so filtering by tag reduces the set
    from data_curator_app import curator_core as core

    core.manage_tags(str(repo), "f3.txt", tags_to_add=["keepme"])  # create state

    res = run_cli(
        str(repo),
        [
            "scan",
            "--sort-by",
            "name",
            "--sort-order",
            "asc",
            "--limit",
            "10",
            "--json",
            "--filter",
            "keepme",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    # Backward compatible field
    assert data["total"] == data["filtered_total"]
    # Raw total equals total number of pending items before filter
    assert data["raw_total"] == 6
    assert data["filtered_total"] == 1
    assert data["files"] == ["f3.txt"]


def test_scan_recursive_include_exclude_and_curatorignore(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    (repo / "sub2").mkdir(parents=True)
    (repo / ".curatorignore").write_text("*.log\n")
    (repo / "root.txt").write_text("r")
    (repo / "note.md").write_text("m")
    (repo / "x.log").write_text("l")
    (repo / "sub" / "a.md").write_text("a")
    (repo / "sub" / "b.txt").write_text("b")
    (repo / "sub2" / "c.log").write_text("c")

    # include only md, exclude sub2/**; .curatorignore should drop *.log
    res = run_cli(
        str(repo),
        [
            "scan",
            "--recursive",
            "--include",
            "**/*.md",
            "--exclude",
            "sub2/**",
            "--json",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert sorted(data["files"]) == ["note.md", "sub/a.md"]


def test_include_exclude_leading_slash_and_casefold(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "Sub").mkdir(parents=True)
    (repo / "Sub" / "A.MD").write_text("a")
    (repo / "sub" / "b.TxT").write_text("b")
    # include with leading slash and different case should match
    res = run_cli(
        str(repo), ["scan", "--recursive", "--include", "/sub/*.md", "--json"]
    )
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert data["files"] == ["Sub/A.MD"]
    # exclude with leading slash and different case should exclude
    res2 = run_cli(
        str(repo), ["scan", "--recursive", "--exclude", "/SUB/*.TXT", "--json"]
    )
    assert res2.returncode == 0
    data2 = json.loads(res2.stdout)
    assert "sub/b.TxT" not in data2["files"]


def test_json_errors_are_standardized(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # rename missing
    r1 = run_cli(str(repo), ["rename", "nope.txt", "new.txt", "--json"])
    assert r1.returncode == 2
    j1 = json.loads(r1.stdout)
    assert j1["code"] == 2 and "not found" in j1["error"].lower()

    # delete missing
    r2 = run_cli(str(repo), ["delete", "nope.txt", "--json"])
    assert r2.returncode == 2
    j2 = json.loads(r2.stdout)
    assert j2["code"] == 2 and "not found" in j2["error"].lower()

    # restore missing
    r3 = run_cli(str(repo), ["restore", "nope.txt", "--json"])
    assert r3.returncode == 2
    j3 = json.loads(r3.stdout)
    assert j3["code"] == 2 and "not found" in j3["error"].lower()


def test_scan_include_expired_flag(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # Two files, one expired keep, one unexpired keep
    (repo / "expired.txt").write_text("x")
    (repo / "active.txt").write_text("y")
    past = "2000-01-01T00:00:00"
    from datetime import datetime, timedelta

    future = (datetime.now() + timedelta(days=10)).isoformat()
    state = {
        "expired.txt": {"status": "keep", "keep_days": 30, "expiry_date": past},
        "active.txt": {"status": "keep", "keep_days": 30, "expiry_date": future},
    }
    (repo / ".curator_state.json").write_text(json.dumps(state))
    # Default scan: none should appear
    res_default = run_cli(str(repo), ["scan", "--json"])
    assert res_default.returncode == 0, res_default.stderr
    d0 = json.loads(res_default.stdout)
    assert "expired.txt" not in d0["files"] and "active.txt" not in d0["files"]
    # With flag: only expired appears
    res = run_cli(str(repo), ["scan", "--include-expired", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data.get("include_expired") is True
    assert data["files"] == ["expired.txt"]
