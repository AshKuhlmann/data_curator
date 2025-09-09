"""
Command-Line Interface (CLI) for the Data Curator application.

This module provides a text-based interface to the core functionalities of the
Data Curator, allowing users to perform curation tasks from the terminal.
It is built using Python's `argparse` module and serves as a wrapper around
the functions exposed by the `curator_core` module.

The CLI supports actions such as scanning for new files, setting file statuses,
managing tags, renaming, deleting, and checking for expired files.

Usage:
    python -m data_curator_app.cli <repository_path> <command> [options]

Example:
    python -m data_curator_app.cli /path/to/my/docs scan --filter "draft"
    python -m data_curator_app.cli /path/to/my/docs status "report.docx" keep_forever
"""

import argparse
import json
import os
import sys
import io
import contextlib
from typing import List, Optional, Any

from data_curator_app import curator_core as core
from data_curator_app import rules_engine as rules


# The CLI functions are simple wrappers around the core logic, ensuring that
# the command-line parsing and execution are cleanly separated from the
# underlying business logic.


def handle_scan(
    repository_path: str,
    filter_term: Optional[str] = None,
    sort_by: str = "name",
    sort_order: str = "asc",
    json_output: bool = False,
    recursive: bool = False,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    include_expired: bool = False,
    quiet: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> None:
    """
    Finds and displays files awaiting review, with filtering and sorting.

    Args:
        repository_path: The path to the repository to scan.
        filter_term: A term to filter the files by.
        sort_by: The key to sort by ('name', 'date', 'size').
        sort_order: The order to sort in ('asc', 'desc').
    """
    # Compute the filtered list that will be displayed/returned.
    files_to_review = core.scan_directory(
        repository_path,
        filter_term=filter_term,
        sort_by=sort_by,
        sort_order=sort_order,
        recursive=recursive,
        include_patterns=include,
        exclude_patterns=exclude,
        include_expired=include_expired,
    )
    total_filtered = len(files_to_review)

    # Also compute the raw total (without the filter term) for better pagination metadata.
    # Keep include/exclude, recursion, and sorting identical to reflect the same universe of files.
    raw_list = core.scan_directory(
        repository_path,
        filter_term=None,
        sort_by=sort_by,
        sort_order=sort_order,
        recursive=recursive,
        include_patterns=include,
        exclude_patterns=exclude,
        include_expired=include_expired,
    )
    raw_total = len(raw_list)
    start = max(0, int(offset)) if offset is not None else 0
    end = start + limit if (limit is not None and limit >= 0) else None
    files_to_review = files_to_review[start:end]
    if json_output:
        print(
            json.dumps(
                {
                    "files": files_to_review,
                    "count": len(files_to_review),
                    # Maintain backward compatibility: `total` equals filtered_total
                    "total": total_filtered,
                    # New fields for richer metadata
                    "filtered_total": total_filtered,
                    "raw_total": raw_total,
                    "limit": limit,
                    "offset": start,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "recursive": bool(recursive),
                    "include_expired": bool(include_expired),
                }
            )
        )
    else:
        if not quiet:
            if files_to_review:
                print("Files available for review:")
                for filename in files_to_review:
                    print(f"  - {filename}")
            else:
                print("No files to review with the current filters.")


def handle_sort(
    repository_path: str,
    sort_by: str,
    sort_order: str,
    json_output: bool = False,
    recursive: bool = False,
    include: Optional[List[str]] = None,
    exclude: Optional[List[str]] = None,
    quiet: bool = False,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> None:
    """A wrapper for handle_scan to sort files."""
    if not json_output and not quiet:
        print(f"Sorting by {sort_by} in {sort_order} order.")
    handle_scan(
        repository_path,
        filter_term=None,
        sort_by=sort_by,
        sort_order=sort_order,
        json_output=json_output,
        recursive=recursive,
        include=include,
        exclude=exclude,
        quiet=quiet,
        limit=limit,
        offset=offset,
    )


def handle_set_status(
    repository_path: str,
    filename: str,
    status: str,
    force: bool = False,
    quiet: bool = False,
    json_output: bool = False,
    days: Optional[int] = None,
) -> None:
    """
    Sets the curation status for a specific file.

    Args:
        repository_path: The path to the repository.
        filename: The name of the file to update.
        status: The new status to assign.
    """
    # Validate status against allowed user set (include legacy alias)
    allowed_user = set(core.USER_ALLOWED_STATUSES) | {"keep_90_days"}
    if status not in allowed_user:
        msg = (
            f"Invalid status '{status}'. Allowed: "
            + ", ".join(sorted(allowed_user))
        )
        if json_output:
            print(json.dumps({"error": msg, "code": 3}))
        else:
            print(f"Error: {msg}")
        sys.exit(3)

    file_path = os.path.join(repository_path, filename)
    if not force and not os.path.exists(file_path):
        msg = f"File '{filename}' not found in repository."
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)
    # Validate days for temporary keep
    if status == "keep" and (days is None or days <= 0):
        msg = "--days must be a positive integer when status is 'keep'"
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)

    try:
        with contextlib.redirect_stdout(io.StringIO()):
            core.update_file_status(repository_path, filename, status, days=days)
    except ValueError as e:
        # Surface core validation errors consistently
        msg = str(e)
        if json_output:
            print(json.dumps({"error": msg, "code": 3}))
        else:
            print(f"Error: {msg}")
        sys.exit(3)
    if json_output:
        out: dict[str, Any] = {
            "result": "updated",
            "filename": filename,
            "status": status,
        }
        if status == "keep" and days is not None:
            out["days"] = days
        print(json.dumps(out))


def handle_manage_tags(
    repository_path: str,
    filename: str,
    tags_to_add: Optional[List[str]] = None,
    tags_to_remove: Optional[List[str]] = None,
    force: bool = False,
    quiet: bool = False,
    json_output: bool = False,
) -> None:
    """
    Adds or removes tags from a file.

    Args:
        repository_path: The path to the repository.
        filename: The name of the file to tag.
        tags_to_add: A list of tags to add.
        tags_to_remove: A list of tags to remove.
    """
    file_path = os.path.join(repository_path, filename)
    if not force and not os.path.exists(file_path):
        msg = f"File '{filename}' not found in repository."
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)
    updated_tags = core.manage_tags(
        repository_path,
        filename,
        tags_to_add=tags_to_add,
        tags_to_remove=tags_to_remove,
    )
    if json_output:
        print(
            json.dumps(
                {"result": "updated", "filename": filename, "tags": updated_tags}
            )
        )
    elif not quiet:
        print(f"Updated tags for '{filename}': {updated_tags}")


def handle_rename(
    repository_path: str,
    old_name: str,
    new_name: str,
    quiet: bool = False,
    json_output: bool = False,
) -> None:
    """
    Renames a file.

    Args:
        repository_path: The path to the repository.
        old_name: The current name of the file.
        new_name: The new name for the file.
    """
    old_filepath = os.path.join(repository_path, old_name)
    if not os.path.exists(old_filepath):
        msg = f"File '{old_name}' not found in repository."
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)
    if os.path.exists(os.path.join(repository_path, new_name)):
        msg = f"A file named '{new_name}' already exists."
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)
    with contextlib.redirect_stdout(io.StringIO()):
        core.rename_file(old_filepath, new_name)
    if json_output:
        print(json.dumps({"result": "renamed", "old": old_name, "new": new_name}))


def handle_delete(
    repository_path: str,
    filename: str,
    yes: bool = False,
    quiet: bool = False,
    json_output: bool = False,
) -> None:
    """
    Moves a file to the curator's trash directory.

    Args:
        repository_path: The path to the repository.
        filename: The name of the file to delete.
    """
    filepath_to_delete = os.path.join(repository_path, filename)
    if not os.path.exists(filepath_to_delete):
        msg = f"File '{filename}' not found in repository."
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)
    if not yes and sys.stdin.isatty():
        try:
            resp = (
                input(f"Delete '{filename}' (move to trash)? [y/N]: ").strip().lower()
            )
        except EOFError:
            resp = "n"
        if resp not in ("y", "yes"):
            if not quiet and not json_output:
                print("Aborted.")
            return
    with contextlib.redirect_stdout(io.StringIO()):
        info = core.delete_file(filepath_to_delete)
    if json_output:
        trash_path = info.get("new_path") if isinstance(info, dict) else None
        print(
            json.dumps(
                {"result": "deleted", "filename": filename, "trash_path": trash_path}
            )
        )


def handle_get_expired(
    repository_path: str,
    json_output: bool = False,
    mark_decide_later: bool = False,
    quiet: bool = False,
) -> None:
    """
    Lists all files whose temporary 'keep' status has expired.

    Args:
        repository_path: The path to the repository.
    """
    expired_files = core.check_for_expired_files(repository_path)
    if mark_decide_later:
        if expired_files:
            updated = core.reset_expired_to_decide_later(repository_path)
            if json_output:
                # Also include details for transparency
                details = core.get_expired_details(repository_path)
                print(
                    json.dumps(
                        {
                            "expired": expired_files,
                            "updated": updated,
                            "details": details,
                        }
                    )
                )
                return
            if not quiet:
                if updated:
                    print("Updated expired files to 'decide_later':")
                    for f in updated:
                        print(f"  - {f}")
                else:
                    print("No expired files to update.")
            return
        else:
            if json_output:
                print(json.dumps({"expired": [], "updated": [], "details": []}))
                return
    if json_output:
        details = core.get_expired_details(repository_path)
        print(json.dumps({"expired": expired_files, "details": details}))
    else:
        if not quiet:
            if expired_files:
                print("The following temporarily kept files have expired:")
                for filename in expired_files:
                    print(f"  - {filename}")
            else:
                print("No temporarily kept files have expired.")


def handle_restore(
    repository_path: str, filename: str, quiet: bool = False, json_output: bool = False
) -> None:
    """Restores a file from the curator trash directory back to the repository."""
    original_path = os.path.join(repository_path, filename)
    trash_path = os.path.join(repository_path, core.TRASH_DIR_NAME, filename)
    if not os.path.exists(trash_path):
        msg = f"File '{filename}' not found in trash."
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)
    with contextlib.redirect_stdout(io.StringIO()):
        ok = core.undo_delete({"original_path": original_path, "new_path": trash_path})
    if not ok:
        sys.exit(1)
    if json_output:
        print(json.dumps({"result": "restored", "filename": filename}))


def handle_trash_list(
    repository_path: str, json_output: bool = False, quiet: bool = False
) -> None:
    """Lists the contents of the curator trash folder."""
    files = core.list_trash_contents(repository_path)
    if json_output:
        print(json.dumps({"files": files, "count": len(files)}))
    else:
        if not quiet:
            if files:
                print("Trash contents:")
                for f in files:
                    print(f"  - {f}")
            else:
                print("Trash is empty.")


def handle_trash_empty(
    repository_path: str,
    yes: bool = False,
    json_output: bool = False,
    quiet: bool = False,
) -> None:
    """Permanently purges the curator trash folder (requires --yes)."""
    if not yes:
        msg = "--yes is required to empty the trash"
        if json_output:
            print(json.dumps({"error": msg, "code": 2}))
        else:
            print(f"Error: {msg}")
        sys.exit(2)
    removed = core.empty_trash(repository_path)
    if json_output:
        print(
            json.dumps({"result": "emptied", "removed": len(removed), "files": removed})
        )
    else:
        if not quiet:
            print(f"Emptied trash: removed {len(removed)} item(s).")


def main() -> None:
    """
    The main entry point for the command-line interface.

    This function sets up the argument parser, defines all available commands
    and their arguments, and dispatches to the appropriate handler function.
    """
    parser = argparse.ArgumentParser(
        description="A command-line interface for the Data Curator.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "repository_path", help="The absolute path to the repository to curate."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce non-essential output.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        help="The action to perform. Available commands are:",
    )

    # --- Scan Command ---
    scan_parser = subparsers.add_parser(
        "scan", help="Scan the repository for files to review."
    )
    scan_parser.add_argument(
        "--filter", help="Filter files by a search term in the filename or tags."
    )
    scan_parser.add_argument(
        "--sort-by",
        choices=["name", "date", "size"],
        default="name",
        help="The key to sort files by (default: name).",
    )
    scan_parser.add_argument(
        "--sort-order",
        choices=["asc", "desc"],
        default="asc",
        help="The order to sort files in (default: asc).",
    )
    scan_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON.",
    )
    scan_parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of results returned.",
    )
    scan_parser.add_argument(
        "--offset",
        type=int,
        help="Offset into the result list before returning items.",
    )
    scan_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan recursively and return relative paths.",
    )
    scan_parser.add_argument(
        "--include",
        action="append",
        metavar="GLOB",
        help="Glob pattern to include (can be repeated).",
    )
    scan_parser.add_argument(
        "--exclude",
        action="append",
        metavar="GLOB",
        help="Glob pattern to exclude (can be repeated).",
    )
    scan_parser.add_argument(
        "--include-expired",
        action="store_true",
        help="Include expired temporary keeps in the scan results.",
    )

    # --- Sort Command ---
    sort_parser = subparsers.add_parser(
        "sort", help="Sort and list files needing review."
    )
    sort_parser.add_argument(
        "sort_by",
        choices=["name", "date", "size"],
        help="The key to sort files by.",
    )
    sort_parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default="asc",
        help="The order to sort in (default: asc).",
    )
    sort_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON.",
    )
    sort_parser.add_argument(
        "--limit",
        type=int,
        help="Limit the number of results returned.",
    )
    sort_parser.add_argument(
        "--offset",
        type=int,
        help="Offset into the result list before returning items.",
    )
    sort_parser.add_argument(
        "--recursive",
        action="store_true",
        help="Scan recursively and return relative paths.",
    )
    sort_parser.add_argument(
        "--include",
        action="append",
        metavar="GLOB",
        help="Glob pattern to include (can be repeated).",
    )
    sort_parser.add_argument(
        "--exclude",
        action="append",
        metavar="GLOB",
        help="Glob pattern to exclude (can be repeated).",
    )

    # --- Status Command ---
    status_parser = subparsers.add_parser(
        "status", help="Update the curation status of a file."
    )
    status_parser.add_argument("filename", help="The name of the file to update.")
    status_parser.add_argument(
        "status",
        help="The new status for the file (keep_forever, keep, decide_later).",
    )
    status_parser.add_argument(
        "--days",
        type=int,
        help="Number of days to keep when using 'keep' (required for 'keep').",
    )
    status_parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass file existence checks and update state anyway.",
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON.",
    )

    # --- Tag Command ---
    tag_parser = subparsers.add_parser("tag", help="Manage tags for a specific file.")
    tag_parser.add_argument("filename", help="The name of the file to tag.")
    tag_parser.add_argument(
        "--add", nargs="+", metavar="TAG", help="One or more tags to add."
    )
    tag_parser.add_argument(
        "--remove", nargs="+", metavar="TAG", help="One or more tags to remove."
    )
    tag_parser.add_argument(
        "--force",
        action="store_true",
        help="Bypass file existence checks and update state anyway.",
    )
    tag_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON.",
    )

    # --- Rename Command ---
    rename_parser = subparsers.add_parser("rename", help="Rename a file.")
    rename_parser.add_argument("old_name", help="The current name of the file.")
    rename_parser.add_argument("new_name", help="The new name for the file.")
    rename_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON.",
    )

    # --- Delete Command ---
    delete_parser = subparsers.add_parser(
        "delete", help="Move a file to the curator trash directory."
    )
    delete_parser.add_argument("filename", help="The name of the file to delete.")
    delete_parser.add_argument(
        "--yes",
        action="store_true",
        help="Do not prompt for confirmation before deleting.",
    )
    delete_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON.",
    )

    # --- Expired Command ---
    expired_parser = subparsers.add_parser(
        "expired", help="List files with an expired temporary 'keep' status."
    )
    expired_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON.",
    )
    expired_parser.add_argument(
        "--mark-decide-later",
        action="store_true",
        help="Reset expired items to 'decide_later'.",
    )

    # --- Restore Command ---
    restore_parser = subparsers.add_parser(
        "restore", help="Restore a file from the curator trash back to the repository."
    )
    restore_parser.add_argument("filename", help="The name of the file to restore.")
    restore_parser.add_argument(
        "--json",
        action="store_true",
        help="Output result in JSON.",
    )

    # --- Trash List Command ---
    trash_list_parser = subparsers.add_parser(
        "trash-list", help="List files currently in the curator trash."
    )
    trash_list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON.",
    )

    # --- Trash Empty Command ---
    trash_empty_parser = subparsers.add_parser(
        "trash-empty", help="Permanently purge the curator trash (requires --yes)."
    )
    trash_empty_parser.add_argument(
        "--yes",
        action="store_true",
        help="Confirm permanent deletion of all items in trash.",
    )
    trash_empty_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON.",
    )

    # --- Status Batch Command ---
    status_batch = subparsers.add_parser(
        "status-batch", help="Batch update the curation status of multiple files."
    )
    status_batch.add_argument(
        "--files", nargs="+", help="One or more filenames to update."
    )
    status_batch.add_argument(
        "--from-file",
        metavar="PATH",
        help="Read newline-delimited filenames from a file.",
    )
    status_batch.add_argument(
        "--stdin",
        action="store_true",
        help="Read newline-delimited filenames from standard input.",
    )
    status_batch.add_argument(
        "--status",
        required=True,
        help="The new status for the files (keep_forever, keep, decide_later).",
    )
    status_batch.add_argument(
        "--days",
        type=int,
        help="Number of days to keep when using 'keep' (required for 'keep').",
    )
    status_batch.add_argument(
        "--force",
        action="store_true",
        help="Bypass file existence checks and update state anyway.",
    )
    status_batch.add_argument(
        "--json",
        action="store_true",
        help="Output aggregated result in JSON.",
    )

    # --- Tag Batch Command ---
    tag_batch = subparsers.add_parser(
        "tag-batch", help="Batch manage tags for multiple files."
    )
    tag_batch.add_argument("--files", nargs="+", help="One or more filenames to tag.")
    tag_batch.add_argument(
        "--from-file",
        metavar="PATH",
        help="Read newline-delimited filenames from a file.",
    )
    tag_batch.add_argument(
        "--stdin",
        action="store_true",
        help="Read newline-delimited filenames from standard input.",
    )
    tag_batch.add_argument(
        "--add", nargs="+", metavar="TAG", help="One or more tags to add."
    )
    tag_batch.add_argument(
        "--remove", nargs="+", metavar="TAG", help="One or more tags to remove."
    )
    tag_batch.add_argument(
        "--force",
        action="store_true",
        help="Bypass file existence checks and update state anyway.",
    )
    tag_batch.add_argument(
        "--json",
        action="store_true",
        help="Output aggregated result in JSON.",
    )

    # --- Rules Command Group ---
    rules_parser = subparsers.add_parser(
        "rules", help="Evaluate or apply curation rules from curator_rules.json"
    )
    rules_sub = rules_parser.add_subparsers(
        dest="rules_command", required=True, help="Rules actions"
    )

    def _add_rules_common(p):
        p.add_argument("--json", action="store_true", help="Output results in JSON.")
        p.add_argument("--recursive", action="store_true", help="Scan recursively.")
        p.add_argument(
            "--include", action="append", metavar="GLOB", help="Include glob"
        )
        p.add_argument(
            "--exclude", action="append", metavar="GLOB", help="Exclude glob"
        )
        p.add_argument(
            "--rules-file",
            metavar="PATH",
            help="Path to rules file (defaults to curator_rules.json in repo)",
        )

    rules_dry = rules_sub.add_parser("dry-run", help="Report matches without changes")
    _add_rules_common(rules_dry)

    rules_apply = rules_sub.add_parser("apply", help="Apply matching actions")
    _add_rules_common(rules_apply)

    args = parser.parse_args()

    def _collect_filenames() -> List[str]:
        names: List[str] = []
        if getattr(args, "files", None):
            names.extend(args.files)
        path = getattr(args, "from_file", None)
        if path:
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if line:
                            names.append(line)
            except OSError:
                # Defer error handling to handlers via empty set; they will return code 3.
                pass
        if getattr(args, "stdin", False):
            try:
                data = sys.stdin.read()
                for line in data.splitlines():
                    line = line.strip()
                    if line:
                        names.append(line)
            except Exception:
                pass
        return names

    # Dispatch the command to its corresponding handler function.
    if args.command == "scan":
        handle_scan(
            args.repository_path,
            filter_term=args.filter,
            sort_by=args.sort_by,
            sort_order=args.sort_order,
            json_output=args.json,
            recursive=args.recursive,
            include=args.include,
            exclude=args.exclude,
            include_expired=getattr(args, "include_expired", False),
            quiet=args.quiet,
            limit=args.limit,
            offset=args.offset,
        )
    elif args.command == "sort":
        handle_sort(
            args.repository_path,
            sort_by=args.sort_by,
            sort_order=args.order,
            json_output=args.json,
            recursive=args.recursive,
            include=args.include,
            exclude=args.exclude,
            quiet=args.quiet,
            limit=args.limit,
            offset=args.offset,
        )
    elif args.command == "status":
        handle_set_status(
            args.repository_path,
            args.filename,
            args.status,
            force=args.force,
            quiet=args.quiet,
            json_output=args.json,
            days=getattr(args, "days", None),
        )
    elif args.command == "tag":
        handle_manage_tags(
            args.repository_path,
            args.filename,
            tags_to_add=args.add,
            tags_to_remove=args.remove,
            force=args.force,
            quiet=args.quiet,
            json_output=args.json,
        )
    elif args.command == "rename":
        handle_rename(
            args.repository_path,
            args.old_name,
            args.new_name,
            quiet=args.quiet,
            json_output=args.json,
        )
    elif args.command == "delete":
        handle_delete(
            args.repository_path,
            args.filename,
            yes=args.yes,
            quiet=args.quiet,
            json_output=args.json,
        )
    elif args.command == "expired":
        handle_get_expired(
            args.repository_path,
            json_output=args.json,
            mark_decide_later=args.mark_decide_later,
            quiet=args.quiet,
        )
    elif args.command == "restore":
        handle_restore(
            args.repository_path,
            args.filename,
            quiet=args.quiet,
            json_output=args.json,
        )
    elif args.command == "trash-list":
        handle_trash_list(
            args.repository_path,
            json_output=args.json,
            quiet=args.quiet,
        )
    elif args.command == "trash-empty":
        handle_trash_empty(
            args.repository_path,
            yes=args.yes,
            json_output=args.json,
            quiet=args.quiet,
        )
    elif args.command == "status-batch":
        filenames = _collect_filenames()
        if not filenames:
            msg = "No filenames provided (use --files, --from-file, or --stdin)."
            if args.json:
                print(json.dumps({"error": msg, "code": 3}))
            else:
                if not args.quiet:
                    print(f"Error: {msg}")
            sys.exit(3)
        handle_status_batch(
            args.repository_path,
            filenames=filenames,
            status=args.status,
            force=args.force,
            json_output=args.json,
            quiet=args.quiet,
            days=getattr(args, "days", None),
        )
    elif args.command == "tag-batch":
        filenames = _collect_filenames()
        if not filenames:
            msg = "No filenames provided (use --files, --from-file, or --stdin)."
            if args.json:
                print(json.dumps({"error": msg, "code": 3}))
            else:
                if not args.quiet:
                    print(f"Error: {msg}")
            sys.exit(3)
        handle_tag_batch(
            args.repository_path,
            filenames=filenames,
            add=args.add,
            remove=args.remove,
            force=args.force,
            json_output=args.json,
            quiet=args.quiet,
        )
    elif args.command == "rules":
        # Build candidate list
        rule_path = (
            args.rules_file
            if getattr(args, "rules_file", None)
            else os.path.join(args.repository_path, rules.RULES_FILENAME)
        )
        rule_set = rules.load_rules(rule_path)
        candidates = core.scan_directory(
            args.repository_path,
            filter_term=None,
            sort_by="name",
            sort_order="asc",
            recursive=args.recursive,
            include_patterns=args.include,
            exclude_patterns=args.exclude,
        )
        results: List[dict] = []
        matched = 0
        applied = 0
        skipped = 0
        for rel in candidates:
            full = os.path.join(args.repository_path, rel)
            action = rules.evaluate_file(rel, full, rule_set)
            if not action or not action.get("action"):
                continue
            matched += 1
            entry = {
                "filename": rel,
                "rule": action.get("name"),
                "action": action.get("action"),
                "action_value": action.get("action_value"),
                "applied": False,
            }
            if args.rules_command == "apply":
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        if action["action"] == "delete":
                            core.delete_file(full)
                            entry["applied"] = True
                            applied += 1
                        elif action["action"] == "add_tag" and action.get(
                            "action_value"
                        ):
                            core.manage_tags(
                                args.repository_path,
                                rel,
                                tags_to_add=[str(action["action_value"])],
                            )
                            entry["applied"] = True
                            applied += 1
                        else:
                            skipped += 1

                except Exception:
                    skipped += 1
            results.append(entry)
        if args.json:
            print(
                json.dumps(
                    {
                        "results": results,
                        "matched": matched,
                        "applied": applied,
                        "skipped": skipped,
                    }
                )
            )
        else:
            if not args.quiet:
                mode = "Applied" if args.rules_command == "apply" else "Matched"
                print(
                    f"Rules {args.rules_command}: {mode} {applied if mode=='Applied' else matched} items"
                )


def handle_status_batch(
    repository_path: str,
    filenames: List[str],
    status: str,
    force: bool = False,
    json_output: bool = False,
    quiet: bool = False,
    days: Optional[int] = None,
) -> None:
    results: List[dict] = []
    updated = 0
    failed = 0
    # Validate status against allowed user set (include legacy alias)
    allowed_user = set(core.USER_ALLOWED_STATUSES) | {"keep_90_days"}
    if status not in allowed_user:
        msg = (
            f"Invalid status '{status}'. Allowed: "
            + ", ".join(sorted(allowed_user))
        )
        if json_output:
            print(json.dumps({"error": msg, "code": 3}))
        else:
            if not quiet:
                print(f"Error: {msg}")
        sys.exit(3)
    # Validate days for temporary keep
    if status == "keep" and (days is None or days <= 0):
        msg = "--days must be a positive integer when status is 'keep'"
        if json_output:
            print(json.dumps({"error": msg, "code": 3}))
        else:
            if not quiet:
                print(f"Error: {msg}")
        sys.exit(3)

    for filename in filenames:
        file_path = os.path.join(repository_path, filename)
        if not force and not os.path.exists(file_path):
            msg = f"File '{filename}' not found in repository."
            results.append({"filename": filename, "error": msg, "code": 2})
            failed += 1
            continue
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                core.update_file_status(repository_path, filename, status, days=days)
        except ValueError as e:
            results.append(
                {"filename": filename, "error": str(e), "code": 3}
            )
            failed += 1
            continue
        entry: dict[str, Any] = {
            "filename": filename,
            "result": "updated",
            "status": status,
        }
        if status == "keep" and days is not None:
            entry["days"] = days
        results.append(entry)
        updated += 1
    if json_output:
        print(json.dumps({"results": results, "updated": updated, "failed": failed}))
    else:
        if not quiet:
            for r in results:
                if "error" in r:
                    print(f"Error: {r['error']}")
                else:
                    print(f"Updated {r['filename']} -> {status}")
    if failed:
        sys.exit(2)


def handle_tag_batch(
    repository_path: str,
    filenames: List[str],
    add: Optional[List[str]] = None,
    remove: Optional[List[str]] = None,
    force: bool = False,
    json_output: bool = False,
    quiet: bool = False,
) -> None:
    results: List[dict] = []
    updated = 0
    failed = 0
    for filename in filenames:
        file_path = os.path.join(repository_path, filename)
        if not force and not os.path.exists(file_path):
            msg = f"File '{filename}' not found in repository."
            results.append({"filename": filename, "error": msg, "code": 2})
            failed += 1
            continue
        with contextlib.redirect_stdout(io.StringIO()):
            tags = core.manage_tags(
                repository_path, filename, tags_to_add=add, tags_to_remove=remove
            )
        results.append({"filename": filename, "result": "updated", "tags": tags})
        updated += 1
    if json_output:
        print(json.dumps({"results": results, "updated": updated, "failed": failed}))
    else:
        if not quiet:
            for r in results:
                if "error" in r:
                    print(f"Error: {r['error']}")
                else:
                    print(f"Updated tags for {r['filename']}: {r['tags']}")
    if failed:
        sys.exit(2)


if __name__ == "__main__":
    main()
