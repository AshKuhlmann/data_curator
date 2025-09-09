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
import fnmatch
from contextlib import contextmanager
import shutil

# The name of the state file, which will be stored in the curated repository.
# Using a leading dot makes it a hidden file on Unix-like systems.
STATE_FILENAME = ".curator_state.json"
# State schema version for forward migrations
SCHEMA_VERSION = 1
# Backup file name used to recover from partial or corrupt writes.
STATE_BACKUP_FILENAME = f"{STATE_FILENAME}.bak"
# A separate lockfile used to coordinate concurrent writers across processes.
LOCK_FILENAME = f"{STATE_FILENAME}.lock"

try:  # Optional, Unix-only
    import fcntl as _fcntl  # type: ignore
except Exception:  # pragma: no cover - on Windows
    _fcntl = None  # type: ignore

try:  # Optional, Windows-only
    import msvcrt as _msvcrt  # type: ignore
except Exception:  # pragma: no cover - on Unix
    _msvcrt = None  # type: ignore


@contextmanager
def _state_file_lock(repository_path: str):
    """Acquire an exclusive cross-process lock for state mutations.

    Uses fcntl.flock on Unix and msvcrt.locking on Windows against a dedicated
    lockfile placed alongside the state file. The lock blocks until acquired.
    """
    lock_path = os.path.join(repository_path, LOCK_FILENAME)
    # Ensure containing directory exists
    os.makedirs(repository_path, exist_ok=True)
    f = open(lock_path, "a+b")
    try:
        if os.name == "nt" and _msvcrt is not None:
            try:
                # Ensure the lock region exists and lock 1 byte from start
                f.seek(0)
                if f.tell() == 0:
                    f.write(b"0")
                    f.flush()
                f.seek(0)
            except Exception:
                pass
            _msvcrt.locking(f.fileno(), _msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
        else:
            if _fcntl is None:
                # Fallback: no-op lock (very rare). Still yield to avoid crashing.
                pass
            else:
                _fcntl.flock(f, _fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt" and _msvcrt is not None:
                try:
                    f.seek(0)
                    _msvcrt.locking(f.fileno(), _msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
                except Exception:
                    pass
            else:
                if _fcntl is not None:
                    try:
                        _fcntl.flock(f, _fcntl.LOCK_UN)
                    except Exception:
                        pass
        finally:
            f.close()


# The name of the directory used to store deleted files, acting as a local trash.
TRASH_DIR_NAME = ".curator_trash"

# Public/user-facing statuses accepted from the CLI
USER_ALLOWED_STATUSES = {"keep_forever", "keep", "decide_later"}
# Internal statuses used by core operations
_INTERNAL_ONLY_STATUSES = {"deleted", "renamed"}
# All statuses the state machine may contain
ALLOWED_STATUSES = USER_ALLOWED_STATUSES | _INTERNAL_ONLY_STATUSES


def _load_state_file(path: str) -> Optional[Dict[str, Any]]:
    """Internal helper to load a state file, returning None on failure."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


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
    backup_filepath = os.path.join(repository_path, STATE_BACKUP_FILENAME)
    # Try primary first
    primary = _load_state_file(state_filepath)
    if primary is not None:
        return primary
    # Fall back to backup if available and valid
    backup = _load_state_file(backup_filepath)
    if backup is not None:
        return backup
    # Default to empty state
    return {}


def _save_state_unlocked(repository_path: str, state: Dict[str, Any]) -> None:
    """
    Saves the current curation state to the JSON file in the repository.

    The state is serialized to JSON with indentation for human readability.

    Args:
        repository_path: The absolute path to the directory being curated.
        state: The dictionary containing the current state to be saved.
    """
    state_filepath = os.path.join(repository_path, STATE_FILENAME)
    backup_filepath = os.path.join(repository_path, STATE_BACKUP_FILENAME)

    # Ensure repository_path exists (os.replace requires same directory for atomicity)
    # Write to a temporary file in the same directory, then atomically replace the state file.
    tmp_path = f"{state_filepath}.tmp-{os.getpid()}-{abs(hash(id(state)))}"
    # Ensure schema version is present and up-to-date before serialization
    try:
        state["_schema_version"] = SCHEMA_VERSION
    except Exception:
        # If state is not a dict for some reason, replace with minimal dict
        state = {"_schema_version": SCHEMA_VERSION}

    # Serialize first to avoid partial writes from json.dump exceptions
    payload = json.dumps(state, indent=4)
    with open(tmp_path, "w", encoding="utf-8") as f:
        f.write(payload)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            # Not all filesystems support fsync; ignore if unavailable
            pass

    # If a current state exists, move it to backup before installing the new file.
    if os.path.exists(state_filepath):
        try:
            os.replace(state_filepath, backup_filepath)
        except OSError:
            # Fallback to a non-atomic copy if rename fails (e.g., cross-fs oddities)
            try:
                import shutil

                shutil.copyfile(state_filepath, backup_filepath)
            except Exception:
                # Proceed without blocking the update.
                pass
    # Atomically replace the state file with the new temp file.
    os.replace(tmp_path, state_filepath)
    # Best-effort: fsync the directory to persist rename operations.
    try:
        dir_fd = os.open(repository_path, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except Exception:
        # Ignore on platforms/filesystems where this isn't supported.
        pass


def save_state(repository_path: str, state: Dict[str, Any]) -> None:
    """
    Save state with an exclusive lock to prevent concurrent writers.

    This is the public entrypoint and will acquire the lock before writing.
    Internal callers that already hold the lock should use _save_state_unlocked.
    """
    with _state_file_lock(repository_path):
        _save_state_unlocked(repository_path, state)


def scan_directory(
    directory_path: str,
    filter_term: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    recursive: bool = False,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    include_expired: bool = False,
    ignore_filename: str = ".curatorignore",
) -> List[str]:
    """
    Scans a directory for files that need review, with sorting options.

    This function lists all files in the given directory, excluding any that have
    already been processed (i.e., have a status other than 'decide_later').
    It can also filter the results based on a search term and sort them.

    Args:
        directory_path: The path to the directory to scan.
        filter_term: An optional string to filter filenames and their tags.
        sort_by: The key to sort by ('name', 'date', 'size').
        sort_order: The order to sort in ('asc', 'desc').

    Returns:
        A list of filenames that are pending review, sorted as requested.
    """
    curation_state = load_state(directory_path)

    # Load ignore patterns from .curatorignore if present.
    ignore_patterns: List[str] = []
    ignore_path = os.path.join(directory_path, ignore_filename)
    if os.path.exists(ignore_path):
        try:
            with open(ignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    ignore_patterns.append(line)
        except IOError:
            pass

    def _norm_path(s: str) -> str:
        return s.replace(os.sep, "/").casefold()

    def _norm_pat(pat: str) -> str:
        pat = pat.lstrip("/")  # treat leading '/' as repo-root
        return pat.replace(os.sep, "/").casefold()

    def is_ignored(relpath: str) -> bool:
        # Apply explicit exclude patterns first, then ignore file patterns.
        rel_cf = _norm_path(relpath)
        base_cf = os.path.basename(relpath).casefold()
        if exclude_patterns:
            for pat in exclude_patterns:
                p = _norm_pat(pat)
                if "/" in p:
                    if fnmatch.fnmatch(rel_cf, p):
                        return True
                    if p.startswith("**/") and fnmatch.fnmatch(base_cf, p[3:]):
                        return True
                else:
                    if fnmatch.fnmatch(base_cf, p):
                        return True
        for pat in ignore_patterns:
            p = _norm_pat(pat)
            if "/" in p:
                if fnmatch.fnmatch(rel_cf, p):
                    return True
                if p.startswith("**/") and fnmatch.fnmatch(base_cf, p[3:]):
                    return True
            else:
                if fnmatch.fnmatch(base_cf, p):
                    return True
        return False

    def is_included(relpath: str) -> bool:
        if include_patterns:
            rel_cf = _norm_path(relpath)
            base_cf = os.path.basename(relpath).casefold()
            for pat in include_patterns:
                p = _norm_pat(pat)
                if "/" in p:
                    if fnmatch.fnmatch(rel_cf, p):
                        return True
                    # Treat leading "**/" as matching basename of files in any folder
                    if p.startswith("**/") and fnmatch.fnmatch(base_cf, p[3:]):
                        return True
                else:
                    if fnmatch.fnmatch(base_cf, p):
                        return True
            return False
        return True

    all_files_in_directory: List[str] = []
    if recursive:
        for root, dirs, files in os.walk(directory_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for name in files:
                if name.startswith("."):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, directory_path)
                # Normalize relpath to use '/' consistently
                rel_norm = rel.replace(os.sep, "/")
                if is_ignored(rel_norm) or not is_included(rel_norm):
                    continue
                if os.path.isfile(full):
                    all_files_in_directory.append(rel_norm)
    else:
        for name in os.listdir(directory_path):
            if name.startswith("."):
                continue
            full = os.path.join(directory_path, name)
            if os.path.isfile(full):
                rel_norm = name
                if is_ignored(rel_norm) or not is_included(rel_norm):
                    continue
                all_files_in_directory.append(rel_norm)

    # Identify files that have already been assigned a permanent status.
    processed_files = set()
    now = datetime.now()
    for filename, metadata in curation_state.items():
        # A malformed state entry might not be a dictionary.
        if isinstance(metadata, dict):
            status = metadata.get("status")
            if status and status != "decide_later":
                # Optionally include expired temporary keeps in the scan results
                if include_expired and status in ("keep", "keep_90_days"):
                    expiry_date_str = metadata.get("expiry_date")
                    if expiry_date_str:
                        try:
                            expiry_date = datetime.fromisoformat(expiry_date_str)
                            if expiry_date < now:
                                # Treat as unprocessed so it appears in the list
                                continue
                        except ValueError:
                            # Invalid date: ignore and treat as processed
                            pass
                processed_files.add(filename)

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

    # --- Sorting Logic ---
    reverse_order = sort_order.lower() == "desc"

    def sort_key(filename: str) -> Any:
        if sort_by == "date":
            return os.path.getmtime(os.path.join(directory_path, filename))
        if sort_by == "size":
            return os.path.getsize(os.path.join(directory_path, filename))
        return filename.casefold()

    return sorted(files_to_review, key=sort_key, reverse=reverse_order)


def update_file_status(
    repository_path: str,
    filename: str,
    status: str,
    tags: Optional[List[str]] = None,
    days: Optional[int] = None,
) -> None:
    """
    Updates the status and optional tags for a file in the state file.

    This function modifies the central state file to record a user's decision
    about a specific file. It can set the status (e.g., 'keep_forever'),
    and assign an expiry date if applicable.

    Args:
        repository_path: The path to the curated repository.
        filename: The name of the file to update.
        status: The new status to assign (e.g., 'keep_forever', 'keep').
        tags: An optional list of tags to associate with the file.
        days: For temporary keeps, the number of days to keep.
    """
    with _state_file_lock(repository_path):
        state = load_state(repository_path)

        # Ensure the file has an entry in the state dictionary.
        state.setdefault(filename, {})
        state[filename].setdefault("tags", [])

        # Add any new tags provided.
        if tags:
            for tag in tags:
                if tag not in state[filename]["tags"]:
                    state[filename]["tags"].append(tag)

        # Backward compatibility: map legacy 'keep_90_days' to new 'keep' with days=90
        effective_status = status
        effective_days = days
        if status == "keep_90_days":
            effective_status = "keep"
            effective_days = 90

        # Validate status against allowed set after legacy mapping
        if effective_status not in ALLOWED_STATUSES:
            raise ValueError(
                f"Invalid status '{status}'. Allowed: {sorted(USER_ALLOWED_STATUSES)}"
            )

        # Update metadata.
        state[filename]["status"] = effective_status
        state[filename]["last_updated"] = datetime.now().astimezone().isoformat()

        # Clear any previous temporary metadata unless setting a temporary keep
        state[filename].pop("expiry_date", None)
        state[filename].pop("keep_days", None)

        # If the status is temporary, calculate and store the expiry date and keep days.
        if effective_status == "keep":
            # Default to 90 days if not provided (defensive default)
            keep_days = int(effective_days) if effective_days is not None else 90
            if keep_days < 1:
                keep_days = 1
            state[filename]["keep_days"] = keep_days
            state[filename]["expiry_date"] = (
                datetime.now() + timedelta(days=keep_days)
            ).isoformat()

        _save_state_unlocked(repository_path, state)
    print(f"Updated '{filename}' to status: {state.get(filename, {}).get('status')}")


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
    with _state_file_lock(repository_path):
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

        _save_state_unlocked(repository_path, state)
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
        with _state_file_lock(directory):
            state = load_state(directory)

            # If the file was tracked, update its key in the state dictionary.
            if old_filename in state:
                state[new_filename] = state.pop(old_filename)
                state[new_filename]["status"] = "renamed"
                state[new_filename]["last_updated"] = (
                    datetime.now().astimezone().isoformat()
                )
            else:
                # If not tracked, create a new entry.
                state[new_filename] = {
                    "status": "renamed",
                    "last_updated": datetime.now().astimezone().isoformat(),
                }

            _save_state_unlocked(directory, state)
        print(f"Renamed '{old_filename}' to '{new_filename}'")
        # Return context needed for a potential undo operation.
        return {"action": "rename", "old_path": old_filepath, "new_path": new_filepath}
    except OSError as e:
        print(f"Error renaming file: {e}")
        return None


def _unique_path(path: str) -> str:
    """Generate a unique path by appending ' (n)' before the extension if needed."""
    base, ext = os.path.splitext(path)
    candidate = path
    n = 1
    while os.path.exists(candidate):
        candidate = f"{base} ({n}){ext}"
        n += 1
    return candidate


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
        new_filepath = _unique_path(new_filepath)
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


def list_trash_contents(repository_path: str) -> List[str]:
    """
    Returns a sorted list of filenames currently in the curator trash.

    Entries are relative to the trash directory and only include files.
    """
    trash_directory = os.path.join(repository_path, TRASH_DIR_NAME)
    if not os.path.exists(trash_directory):
        return []
    try:
        items = []
        for name in os.listdir(trash_directory):
            full = os.path.join(trash_directory, name)
            if os.path.isfile(full):
                items.append(name)
        return sorted(items, key=lambda s: s.casefold())
    except OSError:
        return []


def empty_trash(repository_path: str) -> List[str]:
    """
    Permanently removes all files from the curator trash and returns removed names.

    If the trash directory does not exist, returns an empty list.
    """
    trash_directory = os.path.join(repository_path, TRASH_DIR_NAME)
    if not os.path.exists(trash_directory):
        return []

    removed: List[str] = []
    try:
        # Collect names for reporting before deletion
        for name in os.listdir(trash_directory):
            full = os.path.join(trash_directory, name)
            if os.path.isfile(full):
                removed.append(name)
        # Remove the entire directory tree to be robust, then recreate empty dir
        shutil.rmtree(trash_directory, ignore_errors=True)
        os.makedirs(trash_directory, exist_ok=True)
    except OSError:
        # Best-effort: return what we planned to remove
        pass
    return sorted(removed, key=lambda s: s.casefold())


def reset_expired_to_decide_later(repository_path: str) -> List[str]:
    """
    Resets all expired temporary 'keep' items to 'decide_later'.

    Returns a list of filenames that were updated.
    """
    with _state_file_lock(repository_path):
        state = load_state(repository_path)
        updated: List[str] = []
    now = datetime.now()
    for filename, metadata in list(state.items()):
        if not isinstance(metadata, dict):
            continue
        status = metadata.get("status")
        if status not in ("keep", "keep_90_days"):
            continue
        expiry = metadata.get("expiry_date")
        if not expiry:
            continue
        try:
            dt = datetime.fromisoformat(expiry)
        except ValueError:
            continue
        if dt < now:
            metadata["status"] = "decide_later"
            metadata.pop("expiry_date", None)
            metadata.pop("keep_days", None)
            metadata["last_updated"] = datetime.now().astimezone().isoformat()
            updated.append(filename)
        if updated:
            _save_state_unlocked(repository_path, state)
    return updated


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
        if not isinstance(metadata, dict):
            continue
        if metadata.get("status") in ("keep", "keep_90_days"):
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


def get_expired_details(repository_path: str) -> List[Dict[str, Any]]:
    """
    Returns detailed information for each expired temporary keep item.

    Each entry includes: filename, status, expiry_date, expired flag, and
    days_overdue (integer days the item is past expiry).
    """
    state = load_state(repository_path)
    details: List[Dict[str, Any]] = []
    now = datetime.now()
    for filename, metadata in list(state.items()):
        if not isinstance(metadata, dict):
            continue
        if metadata.get("status") not in ("keep", "keep_90_days"):
            continue
        expiry_date_str = metadata.get("expiry_date")
        if not expiry_date_str:
            continue
        try:
            expiry_dt = datetime.fromisoformat(expiry_date_str)
        except ValueError:
            # Skip invalid dates; check_for_expired_files prints a warning already.
            continue
        if expiry_dt < now:
            days_overdue = max(0, (now - expiry_dt).days)
            details.append(
                {
                    "filename": filename,
                    "status": "keep",
                    "keep_days": metadata.get("keep_days", 90),
                    "expiry_date": expiry_date_str,
                    "expired": True,
                    "days_overdue": days_overdue,
                }
            )
    return details
