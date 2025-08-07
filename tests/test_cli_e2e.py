import subprocess
import sys
import json


def run_cli_command(repo_path, command):
    """Helper function to run the CLI command as a subprocess."""
    # Construct the command to be run
    # We use sys.executable to ensure we're using the same python interpreter
    # that's running the test suite.
    full_command = [
        sys.executable,
        "-m",
        "data_curator_app.cli",
        str(repo_path),
    ] + command.split()

    # Run the command
    result = subprocess.run(
        full_command,
        capture_output=True,
        text=True,
        check=False,  # Don't raise an exception on non-zero exit codes
    )
    return result


def test_scan_and_status_e2e(tmp_path):
    """
    End-to-end test for the scan and status commands.
    1. Creates a test repository with some files.
    2. Runs `scan` and verifies the output.
    3. Runs `status` to update a file's status.
    4. Runs `scan` again and verifies that the updated file is no longer listed.
    """
    # 1. Create a test repository
    repo_path = tmp_path
    (repo_path / "file1.txt").touch()
    (repo_path / "file2.txt").touch()
    (repo_path / "another_file.log").touch()

    # 2. Run `scan` and verify the output
    result = run_cli_command(repo_path, "scan")
    assert result.returncode == 0
    output = result.stdout
    assert "Files available for review:" in output
    assert "file1.txt" in output
    assert "file2.txt" in output
    assert "another_file.log" in output

    # 3. Run `status` to update a file's status
    result = run_cli_command(repo_path, "status file1.txt keep_forever")
    assert result.returncode == 0

    # Verify that the state file was created and has the correct content
    state_file = repo_path / ".curator_state.json"
    assert state_file.exists()
    with open(state_file, "r") as f:
        state = json.load(f)
    assert "file1.txt" in state
    assert state["file1.txt"]["status"] == "keep_forever"

    # 4. Run `scan` again and verify the output
    result = run_cli_command(repo_path, "scan")
    assert result.returncode == 0
    output = result.stdout
    assert "Files available for review:" in output
    assert "file1.txt" not in output
    assert "file2.txt" in output
    assert "another_file.log" in output
