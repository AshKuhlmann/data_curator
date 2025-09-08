# Project Organization

This document provides a detailed overview of the Data Curator project's structure. It is intended to help developers understand the codebase, how different components interact, and where to make changes.

## High-Level Overview

Data Curator is a command-line application for managing and cleaning up files in a directory (a "repository"). The core logic is separated from the CLI, allowing for independent development and testing.

The project uses a state file (`.curator_state.json`) within each curated repository to keep track of file statuses, tags, and other metadata. This allows the application to be stateless and resume curation sessions easily.

## Directory Structure

Here is a breakdown of the key directories and files in the project:

```
.
├── .github/              # GitHub Actions workflows (e.g., CI)
├── data_curator_app/     # The main Python package for the application
│   ├── __init__.py
│   ├── curator_core.py   # Core application logic (state and file management)
│   ├── cli.py            # Command-Line Interface (CLI) entry point
│   └── rules_engine.py   # Automated curation rules engine
├── docs/                 # Project documentation
│   └── project_organization.md
├── scripts/              # Utility and automation scripts
│   └── pre-commit        # Pre-commit hook script
├── tests/                # Automated tests
│   ├── test_curator_core.py
│   └── test_cli.py
├── .curator_state.json   # Example state file (in curated directories)
├── pyproject.toml        # Project metadata and dependencies (Poetry)
└── README.md             # Project overview and user guide
```

## Developer Guidelines

Before contributing, please note the following:

- **Pre-commit Checks**: The `AGENTS.md` file in the root directory specifies pre-commit checks that must be run before finalizing any changes. This ensures code quality and consistency across the project.

## Core Components

The application is divided into several distinct components, each with a specific responsibility.

### 1. Core Logic (`data_curator_app/curator_core.py`)

This is the heart of the application. It has no dependency on the user interface and handles all the fundamental operations:

- **State Management**: Manages the `.curator_state.json` file in each repository. This JSON file stores the status (`keep_forever`, `keep_90_days`, `deleted`, etc.), tags, and modification dates for each file that has been processed.
- **File Operations**: Provides functions to safely rename files and move them to a local trash directory (`.curator_trash`). This includes undo functionality for these operations.
- **File System Scanning**: Scans directories for new or unprocessed files, filtering out those that have already been curated.
- **Tagging**: Allows for adding and removing arbitrary tags to files.
- **Platform Abstraction**: Includes helpers for interacting with the operating system in a cross-platform way (e.g., opening a file explorer).

### 2. Command-Line Interface (`data_curator_app/cli.py`)

Provides a way to interact with the application's core functionality from the command line.

- **Framework**: Uses Python's `argparse` module to define and handle commands and arguments.
- **Functionality**: It serves as a wrapper around `curator_core.py`, exposing functions like `scan`, `status`, `tag`, `rename`, and `delete` as command-line subcommands.
- **Use Cases**: Useful for scripting, automation, or for users who prefer a terminal-based workflow.

### 3. Rules Engine (`data_curator_app/rules_engine.py`)

This component provides a mechanism for automated file curation.

- **Configuration**: Rules are defined in a `curator_rules.json` file in the project's root directory.
- **Logic**: The engine evaluates files against a set of conditions (e.g., "file extension is `.log`" or "file age is greater than 30 days").
- **Actions**: If a file matches the conditions, the engine can suggest an action (e.g., "delete" or "add tag 'archive'").
- **Integration**: This engine is not yet fully integrated into the CLI but provides a foundation for future automation features.

## Testing Strategy (`tests/`)

The project uses `pytest` for testing. The tests are organized to mirror the application's structure:

- **`test_curator_core.py`**: Contains unit tests for the core logic. These tests use a temporary directory (`tmp_path`) to simulate a repository and verify that state changes and file operations work as expected.
- **`test_cli.py`**: Tests the command-line interface. It uses mocking (`unittest.mock`) to isolate the CLI from the core logic, ensuring that the CLI correctly parses arguments and calls the appropriate core functions.

This separation ensures that the core business logic is robust and that the user interfaces are correctly wired to it.

## How It All Works Together

1.  A user provides a repository path to the CLI.
2.  The application calls `curator_core.scan_directory()` to get a list of files to review. This function reads the `.curator_state.json` file to filter out already processed files.
3.  The user performs an action on a file via the CLI (e.g., `status ...`, `tag ...`, `delete ...`).
4.  The CLI calls the relevant function in `curator_core.py` (e.g., `update_file_status()`).
5.  `curator_core.py` updates the state dictionary and saves it back to `.curator_state.json`.

This architecture makes the project easy to maintain and extend. For example, to add a new file action, one would:
1.  Add the logic to `curator_core.py`.
2.  Add a corresponding test in `test_curator_core.py`.
3.  Expose the new function in the CLI (`cli.py`).
