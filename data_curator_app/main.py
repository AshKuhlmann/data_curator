"""Command-line interface for data curator."""

import sys
from .curator_core import scan_directory


def main() -> None:
    """Entry point for the CLI."""
    if len(sys.argv) < 2:
        print("Usage: python -m data_curator_app.main <directory>")
        raise SystemExit(1)

    directory = sys.argv[1]
    files = scan_directory(directory)
    for f in files:
        print(f)


if __name__ == "__main__":
    main()
