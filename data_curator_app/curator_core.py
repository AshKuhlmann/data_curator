import os
import json
from datetime import datetime, timedelta

# The name of the state file, which will be stored in the curated repository.
STATE_FILENAME = ".curator_state.json"


def load_state(repo_path: str) -> dict:
    """Loads the state of processed files from the JSON file in the repo."""
    state_file = os.path.join(repo_path, STATE_FILENAME)
    if not os.path.exists(state_file):
        return {}
    try:
        with open(state_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # If the file is corrupted or unreadable, return an empty state
        return {}


def save_state(repo_path: str, state: dict) -> None:
    """Saves the current state to the JSON file in the repo."""
    state_file = os.path.join(repo_path, STATE_FILENAME)
    with open(state_file, "w") as f:
        json.dump(state, f, indent=4)


def scan_directory(path: str, filter_term: str | None = None) -> list[str]:
    """Scans a directory and returns a list of files matching the optional filter."""
    state = load_state(path)
    all_files = [
        f
        for f in os.listdir(path)
        if os.path.isfile(os.path.join(path, f)) and not f.startswith(".")
    ]
    processed_files = [
        f
        for f, data in state.items()
        if data.get("status") and data.get("status") != "decide_later"
    ]
    files_to_review = [f for f in all_files if f not in processed_files]

    if filter_term:
        term = filter_term.lower()
        filtered: list[str] = []
        for fname in files_to_review:
            tags = state.get(fname, {}).get("tags", [])
            if term in fname.lower() or any(term in t.lower() for t in tags):
                filtered.append(fname)
        files_to_review = filtered

    return files_to_review


def update_file_status(
    repo_path: str, filename: str, status: str, tags: list[str] | None = None
) -> None:
    """Updates the status and optional tags for a file in the state file."""
    state = load_state(repo_path)
    if filename not in state:
        state[filename] = {}
    if "tags" not in state[filename]:
        state[filename]["tags"] = []
    if tags:
        for tag in tags:
            if tag not in state[filename]["tags"]:
                state[filename]["tags"].append(tag)
    state[filename]["status"] = status
    state[filename]["last_updated"] = datetime.now().isoformat()
    if status == "keep_90_days":
        state[filename]["expiry_date"] = (
            datetime.now() + timedelta(days=90)
        ).isoformat()
    save_state(repo_path, state)
    print(f"Updated {filename} to status: {status}")


def manage_tags(
    repo_path: str,
    filename: str,
    tags_to_add: list[str] | None = None,
    tags_to_remove: list[str] | None = None,
) -> list[str]:
    """Add or remove tags for a given filename and return the updated list."""
    state = load_state(repo_path)
    if filename not in state:
        state[filename] = {"tags": []}

    if "tags" not in state[filename]:
        state[filename]["tags"] = []

    if tags_to_add:
        for tag in tags_to_add:
            if tag not in state[filename]["tags"]:
                state[filename]["tags"].append(tag)

    if tags_to_remove:
        state[filename]["tags"] = [
            t for t in state[filename]["tags"] if t not in tags_to_remove
        ]

    save_state(repo_path, state)
    return state[filename]["tags"]


def rename_file(old_path: str, new_name: str) -> dict | None:
    """Renames a file on the filesystem and updates its state."""
    directory = os.path.dirname(old_path)
    state = load_state(directory)
    old_filename = os.path.basename(old_path)
    new_path = os.path.join(directory, new_name)
    if os.path.exists(new_path):
        print(f"Error: A file named {new_name} already exists.")
        return None
    try:
        os.rename(old_path, new_path)
        if old_filename in state:
            state[new_name] = state.pop(old_filename)
            state[new_name]["status"] = "renamed"
            state[new_name]["last_updated"] = datetime.now().isoformat()
        else:
            state[new_name] = {
                "status": "renamed",
                "last_updated": datetime.now().isoformat(),
            }
        save_state(directory, state)
        print(f"Renamed {old_filename} to {new_name}")
        return {"action": "rename", "old_path": old_path, "new_path": new_path}
    except OSError as e:
        print(f"Error renaming file: {e}")
        return None


TRASH_DIR_NAME = ".curator_trash"


def delete_file(file_path: str) -> dict | None:
    """Moves a file to the repository's trash directory and updates its status."""
    directory = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    trash_path = os.path.join(directory, TRASH_DIR_NAME)

    try:
        os.makedirs(trash_path, exist_ok=True)
        new_path = os.path.join(trash_path, filename)
        os.rename(file_path, new_path)

        update_file_status(directory, filename, "deleted")
        print(f"Moved {filename} to trash.")
        return {"action": "delete", "original_path": file_path, "new_path": new_path}
    except OSError as e:
        print(f"Error moving file to trash: {e}")
        return None


def undo_delete(last_action: dict) -> bool:
    """Restores a file from the trash and updates its status."""
    original_path = last_action["original_path"]
    from_path = last_action["new_path"]
    repo_path = os.path.dirname(original_path)
    filename = os.path.basename(original_path)

    try:
        os.rename(from_path, original_path)
        update_file_status(repo_path, filename, "decide_later")
        print(f"Restored {filename} from trash.")
        return True
    except OSError as e:
        print(f"Error restoring file from trash: {e}")
        return False


def open_file_location(file_path):
    """Opens the file's containing folder in the system's file explorer."""
    directory = os.path.dirname(file_path)
    if os.name == "nt":  # Windows
        os.startfile(directory)
    elif os.uname().sysname == "Darwin":  # macOS
        os.system(f'open "{directory}"')
    else:  # Linux
        os.system(f'xdg-open "{directory}"')


def check_for_expired_files(repo_path: str) -> list[str]:
    """Scan the state file for items whose keep period expired."""
    state = load_state(repo_path)
    expired_files: list[str] = []
    today = datetime.now()

    # iterate over copy to allow modification if needed elsewhere
    for filename, data in list(state.items()):
        if data.get("status") == "keep_90_days":
            expiry_date_str = data.get("expiry_date")
            if expiry_date_str:
                expiry_date = datetime.fromisoformat(expiry_date_str)
                if expiry_date < today:
                    expired_files.append(filename)

    return expired_files
