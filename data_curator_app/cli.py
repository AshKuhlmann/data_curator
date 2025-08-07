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
import os
from typing import List, Optional

from data_curator_app import curator_core as core


# The CLI functions are simple wrappers around the core logic, ensuring that
# the command-line parsing and execution are cleanly separated from the
# underlying business logic.


def handle_scan(repository_path: str, filter_term: Optional[str] = None) -> None:
    """
    Finds and displays files awaiting review, with an optional filter.

    Args:
        repository_path: The path to the repository to scan.
        filter_term: A term to filter the files by.
    """
    files_to_review = core.scan_directory(repository_path, filter_term)
    if files_to_review:
        print("Files available for review:")
        for filename in files_to_review:
            print(f"  - {filename}")
    else:
        print("No files to review with the current filters.")


def handle_set_status(repository_path: str, filename: str, status: str) -> None:
    """
    Sets the curation status for a specific file.

    Args:
        repository_path: The path to the repository.
        filename: The name of the file to update.
        status: The new status to assign.
    """
    core.update_file_status(repository_path, filename, status)


def handle_manage_tags(
    repository_path: str,
    filename: str,
    tags_to_add: Optional[List[str]] = None,
    tags_to_remove: Optional[List[str]] = None,
) -> None:
    """
    Adds or removes tags from a file.

    Args:
        repository_path: The path to the repository.
        filename: The name of the file to tag.
        tags_to_add: A list of tags to add.
        tags_to_remove: A list of tags to remove.
    """
    updated_tags = core.manage_tags(
        repository_path,
        filename,
        tags_to_add=tags_to_add,
        tags_to_remove=tags_to_remove,
    )
    print(f"Updated tags for '{filename}': {updated_tags}")


def handle_rename(repository_path: str, old_name: str, new_name: str) -> None:
    """
    Renames a file.

    Args:
        repository_path: The path to the repository.
        old_name: The current name of the file.
        new_name: The new name for the file.
    """
    old_filepath = os.path.join(repository_path, old_name)
    core.rename_file(old_filepath, new_name)


def handle_delete(repository_path: str, filename: str) -> None:
    """
    Moves a file to the curator's trash directory.

    Args:
        repository_path: The path to the repository.
        filename: The name of the file to delete.
    """
    filepath_to_delete = os.path.join(repository_path, filename)
    core.delete_file(filepath_to_delete)


def handle_get_expired(repository_path: str) -> None:
    """
    Lists all files whose temporary 'keep' status has expired.

    Args:
        repository_path: The path to the repository.
    """
    expired_files = core.check_for_expired_files(repository_path)
    if expired_files:
        print("The following temporarily kept files have expired:")
        for filename in expired_files:
            print(f"  - {filename}")
    else:
        print("No temporarily kept files have expired.")


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

    # --- Status Command ---
    status_parser = subparsers.add_parser(
        "status", help="Update the curation status of a file."
    )
    status_parser.add_argument("filename", help="The name of the file to update.")
    status_parser.add_argument(
        "status",
        choices=["keep_forever", "keep_90_days", "decide_later"],
        help="The new status for the file.",
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

    # --- Rename Command ---
    rename_parser = subparsers.add_parser("rename", help="Rename a file.")
    rename_parser.add_argument("old_name", help="The current name of the file.")
    rename_parser.add_argument("new_name", help="The new name for the file.")

    # --- Delete Command ---
    delete_parser = subparsers.add_parser(
        "delete", help="Move a file to the curator trash directory."
    )
    delete_parser.add_argument("filename", help="The name of the file to delete.")

    # --- Expired Command ---
    subparsers.add_parser(
        "expired", help="List files with an expired temporary 'keep' status."
    )

    args = parser.parse_args()

    # Dispatch the command to its corresponding handler function.
    if args.command == "scan":
        handle_scan(args.repository_path, args.filter)
    elif args.command == "status":
        handle_set_status(args.repository_path, args.filename, args.status)
    elif args.command == "tag":
        handle_manage_tags(
            args.repository_path,
            args.filename,
            tags_to_add=args.add,
            tags_to_remove=args.remove,
        )
    elif args.command == "rename":
        handle_rename(args.repository_path, args.old_name, args.new_name)
    elif args.command == "delete":
        handle_delete(args.repository_path, args.filename)
    elif args.command == "expired":
        handle_get_expired(args.repository_path)


if __name__ == "__main__":
    main()
