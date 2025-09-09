import json
import os
import subprocess
import time
from pathlib import Path


def run_cli(repo_path: str, args: list[str]) -> subprocess.CompletedProcess:
    cmd = ["python", "-m", "data_curator_app.cli", repo_path] + args
    return subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )


def write_rules(repo: Path) -> Path:
    rules = [
        {
            "name": "Delete old logs",
            "conditions": [
                {"field": "extension", "operator": "is", "value": ".log"},
                {"field": "age_days", "operator": "gt", "value": 30},
            ],
            "action": "delete",
        },
        {
            "name": "Tag screenshots",
            "conditions": [
                {"field": "filename", "operator": "startswith", "value": "Screenshot"}
            ],
            "action": "add_tag",
            "action_value": "screenshot",
        },
    ]
    p = repo / "curator_rules.json"
    p.write_text(json.dumps(rules))
    return p


def test_rules_dry_run_and_apply(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    old_log = repo / "old.log"
    old_log.write_text("log")
    shot = repo / "Screenshot 2025-01-01.png"
    shot.write_text("img")

    # Set old mtime (> 30 days)
    thirty_one_days = 31 * 24 * 60 * 60
    past = time.time() - thirty_one_days
    os.utime(old_log, (past, past))

    write_rules(repo)

    # Dry run
    r1 = run_cli(str(repo), ["rules", "dry-run", "--json"])
    assert r1.returncode == 0, r1.stderr
    d1 = json.loads(r1.stdout)
    names = {e["filename"]: e for e in d1["results"]}
    assert "old.log" in names and names["old.log"]["action"] == "delete"
    assert shot.name in names and names[shot.name]["action"] == "add_tag"
    assert d1["applied"] == 0

    # Apply
    r2 = run_cli(str(repo), ["rules", "apply", "--json"])
    assert r2.returncode == 0, r2.stderr
    d2 = json.loads(r2.stdout)
    # verify side effects
    trash = repo / ".curator_trash"
    assert not old_log.exists()
    assert trash.exists()
    # tag added to screenshot
    from data_curator_app import curator_core as core

    tags = core.manage_tags(str(repo), shot.name)
    assert "screenshot" in tags
    # counts
    assert d2["applied"] >= 1 and d2["matched"] >= 2
