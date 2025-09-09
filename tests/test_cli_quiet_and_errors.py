import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def test_scan_quiet_suppresses_output(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    res = run_cli(
        str(repo), ["--quiet", "scan"]
    )  # global --quiet must precede subcommand
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_tag_quiet_suppresses_updated_line(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "b.txt").write_text("b")
    res = run_cli(
        str(repo), ["--quiet", "tag", "b.txt", "--add", "one"]
    )  # global quiet must precede subcommand
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_status_batch_quiet_suppresses_output(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.txt").write_text("a")
    res = run_cli(
        str(repo),
        [
            "--quiet",
            "status-batch",
            "--files",
            "a.txt",
            "--status",
            "keep_forever",
        ],
    )
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_rules_quiet_suppresses_summary(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "x.txt").write_text("x")
    # Minimal rule file with no matches is fine; quiet should suppress summary
    (repo / "curator_rules.json").write_text("[]")
    res = run_cli(str(repo), ["--quiet", "rules", "dry-run"])  # non-JSON
    assert res.returncode == 0
    assert res.stdout.strip() == ""


def test_rename_missing_non_json_error(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    res = run_cli(str(repo), ["rename", "nope.txt", "x.txt"])  # non-JSON
    assert res.returncode == 2
    out = res.stdout.strip()
    assert out.startswith("Error:") and "not found" in out


def test_delete_missing_non_json_error(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    res = run_cli(str(repo), ["delete", "nope.txt"])  # non-JSON
    assert res.returncode == 2
    out = res.stdout.strip()
    assert out.startswith("Error:") and "not found" in out


def test_restore_missing_non_json_error(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    res = run_cli(str(repo), ["restore", "nope.txt"])  # non-JSON
    assert res.returncode == 2
    out = res.stdout.strip()
    assert out.startswith("Error:") and "not found" in out
