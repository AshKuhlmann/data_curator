
# User Feedback and Evaluation

**Date:** 2025-07-25

## Evaluation Summary

The Data Curator tool is a GUI-based application for managing and organizing files. The core functionality is sound and the rules engine provides a good way to automate file processing. However, the lack of a command-line interface (CLI) makes it difficult to use in automated workflows or for users who prefer the command line.

## Bugs and Areas for Improvement

### 1. No Command-Line Interface (CLI)

*   **Issue:** The application is purely GUI-based. This is a significant limitation for power users and for integrating the tool into automated scripts or workflows.
*   **Suggestion:** Create a CLI that exposes the core functionalities of the application. This would include features like:
    *   Scanning a directory.
    *   Applying rules from the command line.
    *   Managing the state (e.g., listing processed files, changing file status).

### 2. State File Location

*   **Issue:** The `curator_state.json` file is stored in the project root. This is not ideal as it can clutter the project directory and might be accidentally committed to version control.
*   **Suggestion:** Store the state file in a more appropriate location, such as a user-specific configuration directory (e.g., `~/.config/data_curator/`) or in a hidden directory within the repository (e.g., `.data_curator/`).

### 3. Rules File Location

*   **Issue:** Similar to the state file, the `curator_rules.json` file is located in the project root.
*   **Suggestion:** Allow the user to specify the path to the rules file via a command-line argument or a configuration file. This would provide more flexibility.

### 4. Lack of Documentation

*   **Issue:** There is no documentation on how to create rules for the rules engine. The user has to inspect the code to understand the available fields, operators, and actions.
*   **Suggestion:** Create a `docs/rules_documentation.md` file that explains how to write custom rules. This should include a list of all available fields (e.g., `extension`, `filename`, `age_days`), operators (e.g., `is`, `contains`, `gt`), and actions (e.g., `trash`, `add_tag`).

### 5. Limited Preview Capabilities

*   **Issue:** The GUI can only preview a limited set of file types (images, PDFs, CSVs, and plain text). This could be expanded.
*   **Suggestion:** Add support for previewing other file types, such as code files with syntax highlighting, or other common document formats.

### 6. No Dry-Run Mode for Rules Engine

*   **Issue:** When the rules engine is run, it immediately applies the actions. There is no way to see what the engine *would* do without actually performing the actions.
*   **Suggestion:** Add a `--dry-run` flag to the (future) CLI that would print the actions that would be taken without actually modifying any files. This would give the user more confidence in their rules.
