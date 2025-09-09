import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def test_trash_list_empty_json(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    res = run_cli(str(repo), ["trash-list", "--json"])  # should succeed even if missing
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data == {"files": [], "count": 0}


def test_trash_list_and_empty_with_contents(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    # Create and delete two files, with a collision case
    (repo / "dup.txt").write_text("first")
    r1 = run_cli(str(repo), ["delete", "dup.txt", "--yes", "--json"])
    assert r1.returncode == 0, r1.stderr

    # Recreate the same filename and delete again to force a trash suffix
    (repo / "dup.txt").write_text("second")
    r2 = run_cli(str(repo), ["delete", "dup.txt", "--yes", "--json"])
    assert r2.returncode == 0, r2.stderr

    # Also delete a distinct file
    (repo / "file.txt").write_text("x")
    r3 = run_cli(str(repo), ["delete", "file.txt", "--yes", "--json"])
    assert r3.returncode == 0, r3.stderr

    # List trash contents
    list_res = run_cli(str(repo), ["trash-list", "--json"])
    assert list_res.returncode == 0, list_res.stderr
    listing = json.loads(list_res.stdout)
    files = listing["files"]
    assert listing["count"] == len(files) and listing["count"] >= 3
    # Ensure expected files are present; one of the dup entries will be suffixed
    assert any(name == "dup.txt" for name in files)
    assert any(name.startswith("dup (") and name.endswith(").txt") for name in files)
    assert "file.txt" in files

    # Empty without --yes should fail
    empty_fail = run_cli(str(repo), ["trash-empty", "--json"])  # missing --yes
    assert empty_fail.returncode == 2
    jfail = json.loads(empty_fail.stdout)
    assert jfail.get("code") == 2 and "yes" in jfail.get("error", "").lower()

    # Empty with --yes should succeed and remove all items
    empty_ok = run_cli(str(repo), ["trash-empty", "--yes", "--json"])
    assert empty_ok.returncode == 0, empty_ok.stderr
    e = json.loads(empty_ok.stdout)
    assert e.get("result") == "emptied"
    assert isinstance(e.get("removed"), int) and e.get("removed") >= 3
    assert isinstance(e.get("files"), list) and len(e["files"]) == e["removed"]

    # After emptying, listing should be empty
    list_after = run_cli(str(repo), ["trash-list", "--json"])
    assert list_after.returncode == 0
    assert json.loads(list_after.stdout) == {"files": [], "count": 0}
