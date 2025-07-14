import os
import json
from datetime import datetime, timedelta

# Note: The state file path needs to be relative to the project root
STATE_FILE = "curator_state.json"
TARGET_REPOSITORY = ""  # We will set this from the GUI


def load_state():
    """Loads the state of processed files from the JSON file."""
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    """Saves the current state to the JSON file."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)


def scan_directory(path, filter_term: str | None = None):
    """Scans a directory and returns a list of files matching the optional filter."""
    state = load_state()
    all_files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
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


def update_file_status(filename, status, tags: list[str] | None = None):
    """Updates the status and optional tags for a file in the state file."""
    state = load_state()
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
    save_state(state)
    print(f"Updated {filename} to status: {status}")


def manage_tags(
    filename: str,
    tags_to_add: list[str] | None = None,
    tags_to_remove: list[str] | None = None,
) -> list[str]:
    """Add or remove tags for a given filename and return the updated list."""
    state = load_state()
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

    save_state(state)
    return state[filename]["tags"]


def rename_file(old_path, new_name):
    """Renames a file on the filesystem and updates its state."""
    state = load_state()
    old_filename = os.path.basename(old_path)
    directory = os.path.dirname(old_path)
    new_path = os.path.join(directory, new_name)
    if os.path.exists(new_path):
        print(f"Error: A file named {new_name} already exists.")
        return False
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
        save_state(state)
        print(f"Renamed {old_filename} to {new_name}")
        return True
    except OSError as e:
        print(f"Error renaming file: {e}")
        return False


def delete_file(file_path):
    """Deletes a file from the filesystem."""
    try:
        os.remove(file_path)
        update_file_status(os.path.basename(file_path), "deleted")
        print(f"Deleted {os.path.basename(file_path)}")
        return True
    except OSError as e:
        print(f"Error deleting file: {e}")
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


def check_for_expired_files():
    """Scan the state file for items whose keep period expired."""
    state = load_state()
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
