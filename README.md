# Data Curator

Data Curator is a command‑line tool for curating files in a folder one at a time. It remembers what you have already reviewed, lets you tag and set statuses, and supports safe delete/restore via a curator trash folder. The state of your decisions is saved locally so you can resume where you left off.

## Key Features

- Intelligent scanning: skips files already curated; supports include/exclude and recursion.
- Powerful actions: keep forever, keep temporarily (with expiry), decide later, rename, delete, restore.
- Tagging: add/remove tags; filter by tag via scan filters.
- JSON output: scriptable results for `scan`, `sort`, and `expired`.
- Batch modes: update many files via file/stdin lists.

## Project Structure

The repository is organized to keep core logic separate from the CLI and tests:

- `data_curator_app/`
  - `curator_core.py`: state, scanning, tagging, file ops (rename/delete/restore), expired handling
  - `cli.py`: argument parsing and command handlers for the CLI
  - `rules_engine.py`: simple rule evaluation on file attributes
- `docs/`
  - `PROJECT_STRUCTURE.md`: deeper overview of components and flow
  - `SCHEMA.md`: notes on state structure and versioning
  - `developer_diary.md`: dated, actionable improvement checklist
- `scripts/pre-commit`: local CI gate (format/lint/type/test/install)
- `tests/`: pytest suite for core and CLI
- `pyproject.toml` / `poetry.lock`: project metadata and dev tool config

Common files created in curated folders:

- `.curator_state.json`: per-repo state (status, tags, timestamps, optional expiry)
- `.curator_trash/`: safe “trash” for soft-deletes
- `.curatorignore` (optional): ignore patterns for scans

## Installation

### Running from source

Assuming you have cloned the repository and are in the project's root directory:

```bash
# Install dependencies
pip install poetry
poetry install

# Use the CLI
poetry run data-curator /path/to/repo scan --json
```

## Updating

To get the latest features and bugfixes, you should update Data Curator regularly. The process depends on how you installed the application.

### From a Released Executable

If you are using a pre-built executable, visit the project's Releases page, download the latest version for your operating system, and replace your old executable with the new one.

### From Source

If you are running the application from source, navigate to the project's root directory in your terminal and run the following commands:

```bash
# 1. Pull the latest changes from the repository
git pull

# 2. Install any new or updated dependencies
poetry install
```

## How to Use

Run `data-curator` with a repository path and a subcommand. See examples below.

## Contributing

Contributions are welcome! Please open an issue to discuss your ideas. If you would like to submit code:

1. Fork the repository and create a branch for your feature.
2. Commit your changes and push the branch.
3. Open a pull request.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for details.

## Installation for Development

Before finalizing any pull request, run:

```bash
pip install poetry
poetry install
./scripts/pre-commit
```

## CLI Usage

After installing in editable mode, a `data-curator` command is available.

Basic examples:

- Scan current repo and print as JSON (includes paging metadata):

  `data-curator /path/to/repo scan --json`

  JSON fields include: `files`, `count`, `total` (same as `filtered_total`), `filtered_total`, `raw_total`, `limit`, `offset`, `sort_by`, `sort_order`, `recursive`.

- Sort by size, descending, recursively including only markdown files:

  `data-curator /path/to/repo sort size --order desc --recursive --include "**/*.md"`

- Delete a file (moves to `.curator_trash`) with no prompt, then restore it:

  `data-curator /path/to/repo delete myfile.txt --yes`

  `data-curator /path/to/repo restore myfile.txt`

- List and empty trash contents:

  `data-curator /path/to/repo trash-list --json`

  `data-curator /path/to/repo trash-empty --yes --json`

- Update status and tags (with existence check bypass):

  `data-curator /path/to/repo status notes.txt keep_forever --force`

  `data-curator /path/to/repo tag notes.txt --add projectX urgent`

- Handle expired temporary keeps:

  `data-curator /path/to/repo expired --json`

  `data-curator /path/to/repo expired --mark-decide-later`

  In `--json` mode, expired output includes `details` with entries of the form
  `{ "filename", "status", "expiry_date", "expired": true, "days_overdue" }`.
  Running with `--mark-decide-later --json` returns both `expired` and `updated` arrays;
  subsequent runs are idempotent and will report `updated: []` when nothing remains to change.

- Batch inputs from file/stdin:

  `data-curator /path/to/repo status-batch --from-file files.txt --status keep_forever --json`

  `printf "a.txt\nb.txt\n" | data-curator /path/to/repo tag-batch --stdin --add important --json`

- Evaluate/apply rules from curator_rules.json:

  `data-curator /path/to/repo rules dry-run --json`

  `data-curator /path/to/repo rules apply --json`

  Options: `--recursive`, `--include GLOB`, `--exclude GLOB`, `--rules-file PATH`

Flags worth noting:

- `--recursive`: Include files in subdirectories; results are relative paths.
- `--include/--exclude`: Repeatable glob patterns to include/exclude.
- `--json`: Machine-readable output for `scan`, `sort`, and `expired`.
- `--yes`: Skip delete confirmation prompts.
- `--force`: Allow state updates even if the file does not exist.
- `--quiet`: Reduce non-essential output.
- `--include-expired`: Include expired temporary keeps in scans.

## Exit Codes and JSON Errors

- 0: Success.
- 1: Generic failure (unexpected error).
- 2: Not found or operation failed (e.g., missing file; batch with one or more failures).
- 3: Invalid input (e.g., missing required filenames for batch operations).

Structured JSON errors follow the shape:

`{ "error": "human-readable message", "code": <exit_code> }`

Notes:
- Non-JSON mode prints errors prefixed with `Error:` and uses the same exit codes.
- Batch commands return aggregated JSON with per-item results; any per-item failure sets the process exit code to 2. Example shape:

`{ "results": [ {"filename": "a.txt", "result": "updated"}, {"filename": "missing.txt", "error": "...", "code": 2 } ], "updated": 1, "failed": 1 }`

## Future Work

Planned enhancements and areas under consideration (see `docs/developer_diary.md` for the detailed checklist):

- CLI/UX
  - `open`/`reveal` command to show a file in the system file explorer
  - Status validation with helpful errors; `list --status <status>` for curated items
  - `--exclude-dir` convenience, `--sort-by created|accessed` (platform-aware)
  - Streaming `--json-lines` output for large scans; improved stdout/stderr hygiene
  - `init` command for baseline `.curatorignore` and `.gitignore` entries
- Rules Engine
  - `rules test --file` for per-file evaluation; `rules metrics` summaries
  - JSON Schema validation for rules with detailed error locations
- State/Trash
  - Configurable state/trash locations and import/export/diff utilities
- Testing & Quality Gates
  - Coverage gating; exit code consistency tests; multi-process lock contention tests
- Packaging & CI/CD
  - `pipx` install path, typed package (`py.typed`), enriched metadata
  - Release pipeline to PyPI and wider CI matrix (Ubuntu/macOS/Windows, Python 3.11–3.13)
- Platform
  - Windows long-path guidance, SMB/NFS lock notes, macOS Unicode normalization tests
