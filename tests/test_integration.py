import json
import subprocess
from typing import List

# The name of the state file used by the application
STATE_FILENAME = ".curator_state.json"
TRASH_DIR_NAME = ".curator_trash"


def run_cli(repo_path: str, command: List[str]) -> subprocess.CompletedProcess:
    """Helper function to run the CLI in a subprocess."""
    base_command = ["python", "-m", "data_curator_app.cli", repo_path]
    full_command = base_command + command
    return subprocess.run(full_command, capture_output=True, text=True, check=False)


def test_cli_delete_end_to_end(tmp_path):
    """
    Tests the 'delete' command from end-to-end by running the CLI as a
    subprocess and verifying the results on the filesystem.
    """
    repo_path = str(tmp_path)
    file_to_delete = tmp_path / "file_to_delete.txt"
    file_to_delete.write_text("This file will be deleted.")

    # Run the CLI 'delete' command
    result = run_cli(repo_path, ["delete", "file_to_delete.txt"])
    assert result.returncode == 0

    # 1. Verify the file was moved to the trash directory
    trash_path = tmp_path / TRASH_DIR_NAME / "file_to_delete.txt"
    assert not file_to_delete.exists()
    assert trash_path.exists()
    assert trash_path.read_text() == "This file will be deleted."

    # 2. Verify the state file was updated correctly
    state_file = tmp_path / STATE_FILENAME
    assert state_file.exists()
    state = json.loads(state_file.read_text())
    assert "file_to_delete.txt" in state
    assert state["file_to_delete.txt"]["status"] == "deleted"
