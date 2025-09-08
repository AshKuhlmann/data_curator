# Data Curator

Data Curator is a command‑line tool for curating files in a folder one at a time. It remembers what you have already reviewed, lets you tag and set statuses, and supports safe delete/restore via a curator trash folder. The state of your decisions is saved locally so you can resume where you left off.

## Key Features

- Intelligent scanning: skips files already curated; supports include/exclude and recursion.
- Powerful actions: keep forever, keep temporarily (with expiry), decide later, rename, delete, restore.
- Tagging: add/remove tags; filter by tag via scan filters.
- JSON output: scriptable results for `scan`, `sort`, and `expired`.
- Batch modes: update many files via file/stdin lists.

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
