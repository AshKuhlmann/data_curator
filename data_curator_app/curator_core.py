"""
Core logic for the Data Curator application.

This module provides the backend functionality for managing the file curation process.
It handles loading and saving the curation state, scanning directories for new files,
updating file statuses, managing tags, and performing file operations like
renaming and deleting. The state is stored in a JSON file within the repository
being curated, allowing for persistent, session-independent tracking of decisions.
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# The name of the state file, which will be stored in the curated repository.
# Using a leading dot makes it a hidden file on Unix-like systems.
STATE_FILENAME = ".curator_state.json"

# The name of the directory used to store deleted files, acting as a local trash.
TRASH_DIR_NAME = ".curator_trash"


def load_state(repository_path: str) -> Dict[str, Any]:
    """
    Loads the state of processed files from the JSON file in the repository.

    If the state file does not exist, is empty, or is corrupted, an empty
    dictionary is returned, signifying a fresh start.

    Args:
        repository_path: The absolute path to the directory being curated.

    Returns:
        A dictionary where keys are filenames and values are their metadata,
        such as status, tags, and timestamps.
    """
    state_filepath = os.path.join(repository_path, STATE_FILENAME)
    if not os.path.exists(state_filepath):
        return {}
    try:
        with open(state_filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # If the file is corrupted or unreadable, return an empty state to prevent crashing.
        return {}


def save_state(repository_path: str, state: Dict[str, Any]) -> None:
    """
    Saves the current curation state to the JSON file in the repository.

    The state is serialized to JSON with indentation for human readability.

    Args:
        repository_path: The absolute path to the directory being curated.
        state: The dictionary containing the current state to be saved.
    """
    state_filepath = os.path.join(repository_path, STATE_FILENAME)
    with open(state_filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=4)


def scan_directory(directory_path: str, filter_term: Optional[str] = None) -> List[str]:
    """
    Scans a directory for files that need review.

    This function lists all files in the given directory, excluding any that have
    already been processed (i.e., have a status other than 'decide_later').
    It can also filter the results based on a search term.

    Args:
        directory_path: The path to the directory to scan.
        filter_term: An optional string to filter filenames and their tags. The
                     filter is case-insensitive.

    Returns:
        A list of filenames that are pending review.
    """
    curation_state = load_state(directory_path)
    all_files_in_directory = [
        f
        for f in os.listdir(directory_path)
        if os.path.isfile(os.path.join(directory_path, f)) and not f.startswith(".")
    ]

    # Identify files that have already been assigned a permanent status.
    processed_files = {
        filename
        for filename, metadata in curation_state.items()
        if metadata.get("status") and metadata.get("status") != "decide_later"
    }

    # Files to review are those present in the directory but not in the processed set.
    files_to_review = [f for f in all_files_in_directory if f not in processed_files]

    # If a filter term is provided, narrow down the list.
    if filter_term:
        normalized_term = filter_term.lower()
        filtered_list: List[str] = []
        for filename in files_to_review:
            tags = curation_state.get(filename, {}).get("tags", [])
            # Check if the term appears in the filename or any of its tags.
            if normalized_term in filename.lower() or any(
                normalized_term in tag.lower() for tag in tags
            ):
                filtered_list.append(filename)
        files_to_review = filtered_list

    return sorted(files_to_review)  # Sort for consistent order.


def update_file_status(
    repository_path: str,
    filename: str,
    status: str,
    tags: Optional[List[str]] = None,
) -> None:
    """
    Updates the status and optional tags for a file in the state file.

    This function modifies the central state file to record a user's decision
    about a specific file. It can set the status (e.g., 'keep_forever'),
    and assign an expiry date if applicable.

    Args:
        repository_path: The path to the curated repository.
        filename: The name of the file to update.
        status: The new status to assign (e.g., 'keep_forever', 'keep_90_days').
        tags: An optional list of tags to associate with the file.
    """
    state = load_state(repository_path)

    # Ensure the file has an entry in the state dictionary.
    state.setdefault(filename, {})
    state[filename].setdefault("tags", [])

    # Add any new tags provided.
    if tags:
        for tag in tags:
            if tag not in state[filename]["tags"]:
                state[filename]["tags"].append(tag)

    # Update metadata.
    state[filename]["status"] = status
    state[filename]["last_updated"] = datetime.now().isoformat()

    # If the status is temporary, calculate and store the expiry date.
    if status == "keep_90_days":
        state[filename]["expiry_date"] = (
            datetime.now() + timedelta(days=90)
        ).isoformat()

    save_state(repository_path, state)
    print(f"Updated '{filename}' to status: {status}")


def manage_tags(
    repository_path: str,
    filename: str,
    tags_to_add: Optional[List[str]] = None,
    tags_to_remove: Optional[List[str]] = None,
) -> List[str]:
    """
    Adds or removes tags for a file and returns the updated list of tags.

    Args:
        repository_path: The path to the curated repository.
        filename: The name of the file whose tags are to be managed.
        tags_to_add: A list of tags to add to the file.
        tags_to_remove: A list of tags to remove from the file.

    Returns:
        The final list of tags associated with the file.
    """
    state = load_state(repository_path)
    state.setdefault(filename, {}).setdefault("tags", [])

    current_tags = state[filename]["tags"]

    # Add new tags, ensuring no duplicates.
    if tags_to_add:
        for tag in tags_to_add:
            if tag not in current_tags:
                current_tags.append(tag)

    # Remove specified tags.
    if tags_to_remove:
        state[filename]["tags"] = [
            tag for tag in current_tags if tag not in tags_to_remove
        ]

    save_state(repository_path, state)
    return state[filename]["tags"]


def rename_file(old_filepath: str, new_filename: str) -> Optional[Dict[str, Any]]:
    """
    Renames a file on the filesystem and updates its record in the state file.

    If the original file was tracked in the state file, its record is updated
    to reflect the new filename.

    Args:
        old_filepath: The current full path to the file.
        new_filename: The new name for the file (not a path).

    Returns:
        A dictionary containing details of the action for undo purposes,
        or None if the operation fails.
    """
    directory = os.path.dirname(old_filepath)
    old_filename = os.path.basename(old_filepath)
    new_filepath = os.path.join(directory, new_filename)

    if os.path.exists(new_filepath):
        print(f"Error: A file named '{new_filename}' already exists.")
        return None

    try:
        os.rename(old_filepath, new_filepath)
        state = load_state(directory)

        # If the file was tracked, update its key in the state dictionary.
        if old_filename in state:
            state[new_filename] = state.pop(old_filename)
            state[new_filename]["status"] = "renamed"
            state[new_filename]["last_updated"] = datetime.now().isoformat()
        else:
            # If not tracked, create a new entry.
            state[new_filename] = {
                "status": "renamed",
                "last_updated": datetime.now().isoformat(),
            }

        save_state(directory, state)
        print(f"Renamed '{old_filename}' to '{new_filename}'")
        # Return context needed for a potential undo operation.
        return {"action": "rename", "old_path": old_filepath, "new_path": new_filepath}
    except OSError as e:
        print(f"Error renaming file: {e}")
        return None


def delete_file(filepath: str) -> Optional[Dict[str, Any]]:
    """
    Moves a file to a dedicated trash directory within the repository.

    This provides a safer alternative to permanent deletion, allowing for recovery.
    The file's status is updated to 'deleted' in the state file.

    Args:
        filepath: The full path of the file to be deleted.

    Returns:
        A dictionary with action details for undo, or None on failure.
    """
    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    trash_directory = os.path.join(directory, TRASH_DIR_NAME)

    try:
        os.makedirs(trash_directory, exist_ok=True)
        new_filepath = os.path.join(trash_directory, filename)
        os.rename(filepath, new_filepath)

        update_file_status(directory, filename, "deleted")
        print(f"Moved '{filename}' to trash.")
        return {
            "action": "delete",
            "original_path": filepath,
            "new_path": new_filepath,
        }
    except OSError as e:
        print(f"Error moving file to trash: {e}")
        return None


def undo_delete(last_action: Dict[str, Any]) -> bool:
    """
    Restores a file from the trash directory back to its original location.

    This function reverses a 'delete' operation. The file's status is reverted
    to 'decide_later' to allow the user to re-evaluate it.

    Args:
        last_action: The action dictionary returned by a successful delete_file call.

    Returns:
        True if the restoration was successful, False otherwise.
    """
    original_path = last_action["original_path"]
    from_path = last_action["new_path"]
    repository_path = os.path.dirname(original_path)
    filename = os.path.basename(original_path)

    try:
        os.rename(from_path, original_path)
        # Revert status so the file reappears in the review queue.
        update_file_status(repository_path, filename, "decide_later")
        print(f"Restored '{filename}' from trash.")
        return True
    except OSError as e:
        print(f"Error restoring file from trash: {e}")
        return False


def open_file_location(filepath: str) -> None:
    """
    Opens the file's containing folder in the system's default file explorer.

    This is a cross-platform implementation that supports Windows, macOS, and Linux.

    Args:
        filepath: The path to the file whose location is to be opened.
    """
    directory = os.path.dirname(filepath)
    try:
        if os.name == "nt":  # Windows
            os.startfile(directory)  # type: ignore[attr-defined]
        elif os.uname().sysname == "Darwin":  # macOS
            subprocess.run(["open", directory], check=True)
        else:  # Linux and other Unix-likes
            subprocess.run(["xdg-open", directory], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        print(f"Error opening file location: {e}")


def check_for_expired_files(repository_path: str) -> List[str]:
    """
    Scans the state file for items whose temporary 'keep' period has expired.

    Args:
        repository_path: The path to the curated repository.

    Returns:
        A list of filenames of files that have expired.
    """
    state = load_state(repository_path)
    expired_files: List[str] = []
    current_time = datetime.now()

    # Iterate over a copy of the items to avoid issues with potential modifications.
    for filename, metadata in list(state.items()):
        if metadata.get("status") == "keep_90_days":
            expiry_date_str = metadata.get("expiry_date")
            if expiry_date_str:
                try:
                    expiry_date = datetime.fromisoformat(expiry_date_str)
                    if expiry_date < current_time:
                        expired_files.append(filename)
                except ValueError:
                    # Handle cases where the date format is invalid.
                    print(f"Warning: Invalid date format for '{filename}'")

    return expired_files
