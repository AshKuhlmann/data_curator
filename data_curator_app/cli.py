import argparse
import os
from data_curator_app import curator_core as core


def scan(repo_path, filter_term=None):
    """Wrapper for core.scan_directory."""
    return core.scan_directory(repo_path, filter_term)


def set_status(filename, status):
    """Wrapper for core.update_file_status."""
    core.update_file_status(filename, status)


def manage_tags(filename, tags_to_add=None, tags_to_remove=None):
    """Wrapper for core.manage_tags."""
    return core.manage_tags(
        filename, tags_to_add=tags_to_add, tags_to_remove=tags_to_remove
    )


def rename(repo_path, old_name, new_name):
    """Wrapper for core.rename_file."""
    old_path = os.path.join(repo_path, old_name)
    return core.rename_file(old_path, new_name)


def delete(repo_path, filename):
    """Wrapper for core.delete_file."""
    file_path = os.path.join(repo_path, filename)
    return core.delete_file(file_path)


def get_expired():
    """Wrapper for core.check_for_expired_files."""
    return core.check_for_expired_files()


def main():
    """The main entry point for the command-line interface."""
    parser = argparse.ArgumentParser(
        description="A command-line interface for Data Curator."
    )
    parser.add_argument("repo_path", help="The path to the repository to curate.")

    subparsers = parser.add_subparsers(
        dest="command", required=True, help="Available commands"
    )

    # Scan command
    scan_parser = subparsers.add_parser(
        "scan", help="Scan the repository for files to review."
    )
    scan_parser.add_argument("--filter", help="Filter files by a search term.")

    # Status command
    status_parser = subparsers.add_parser("status", help="Update the status of a file.")
    status_parser.add_argument("filename", help="The name of the file to update.")
    status_parser.add_argument(
        "status",
        choices=["keep_forever", "keep_90_days", "decide_later"],
        help="The new status for the file.",
    )

    # Tag command
    tag_parser = subparsers.add_parser("tag", help="Manage tags for a file.")
    tag_parser.add_argument("filename", help="The name of the file to tag.")
    tag_parser.add_argument("--add", nargs="+", help="Tags to add.")
    tag_parser.add_argument("--remove", nargs="+", help="Tags to remove.")

    # Rename command
    rename_parser = subparsers.add_parser("rename", help="Rename a file.")
    rename_parser.add_argument("old_name", help="The current name of the file.")
    rename_parser.add_argument("new_name", help="The new name for the file.")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a file.")
    delete_parser.add_argument("filename", help="The name of the file to delete.")

    # Expired command
    subparsers.add_parser("expired", help="List files with expired temporary status.")

    args = parser.parse_args()

    # Dispatch commands to their respective handlers
    if args.command == "scan":
        files = scan(args.repo_path, args.filter)
        if files:
            print("Files available for review:")
            for f in files:
                print(f"  - {f}")
        else:
            print("No files to review with the current filters.")

    elif args.command == "status":
        set_status(args.filename, args.status)

    elif args.command == "tag":
        tags = manage_tags(
            args.filename, tags_to_add=args.add, tags_to_remove=args.remove
        )
        print(f"Tags for {args.filename}: {tags}")

    elif args.command == "rename":
        rename(args.repo_path, args.old_name, args.new_name)

    elif args.command == "delete":
        delete(args.repo_path, args.filename)

    elif args.command == "expired":
        expired_files = get_expired()
        if expired_files:
            print("The following files have expired:")
            for f in expired_files:
                print(f"  - {f}")
        else:
            print("No files have expired.")


if __name__ == "__main__":
    main()
