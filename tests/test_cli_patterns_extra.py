import json
import subprocess
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def test_unicode_include_and_dotfiles_skipped(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo).mkdir()
    # Unicode filename
    unic = "unicodé🔥.txt"
    (repo / unic).write_text("u")
    # Hidden dotfile should be skipped regardless
    (repo / ".hidden.txt").write_text("h")

    # Include with different case should still match unicode name
    res = run_cli(str(repo), ["scan", "--include", "UNICODÉ🔥.TXT", "--json"])
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert data["files"] == [unic]

    # Even with a broad include, dotfiles are not listed
    res2 = run_cli(str(repo), ["scan", "--include", "*", "--json"])
    assert res2.returncode == 0, res2.stderr
    d2 = json.loads(res2.stdout)
    assert ".hidden.txt" not in d2["files"]


def test_exclude_overrides_include_and_recursive_globs(tmp_path: Path):
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    (repo / "sub" / "inner").mkdir(parents=True)
    (repo / "a.txt").write_text("a")
    (repo / "sub" / "b.md").write_text("b")
    (repo / "sub" / "inner" / "c.LOG").write_text("c")

    # Include everything md/log, but exclude sub/** should win
    res = run_cli(
        str(repo),
        [
            "scan",
            "--recursive",
            "--include",
            "**/*.md",
            "--include",
            "**/*.log",
            "--exclude",
            "sub/**",
            "--json",
        ],
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout)
    assert "sub/b.md" not in data["files"]
    assert "sub/inner/c.LOG" not in data["files"]

    # Leading slash and case-insensitive recursive match
    res2 = run_cli(
        str(repo),
        [
            "scan",
            "--recursive",
            "--include",
            "/SUB/INNER/*.log",
            "--json",
        ],
    )
    assert res2.returncode == 0, res2.stderr
    d2 = json.loads(res2.stdout)
    assert d2["files"] == ["sub/inner/c.LOG"]
