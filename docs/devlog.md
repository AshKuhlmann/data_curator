Data Curator – Polish Suggestions and Notes

Date: 2025-08-19

Summary
- After end-to-end CLI testing (sorting, status/tag/rename/delete, expired) and additional nuanced scenarios (unicode, spaced paths, zero-byte/large files, hidden files, subdirectories, error paths), the app works reliably. Below are targeted improvements to polish UX, safety, and integration.

UX & CLI
- Default repo: Make `repository_path` optional (default to `.`) and add `-C/--repo`.
- Validate inputs: For `status`, `tag`, `rename`, `delete`, check file existence and provide friendly messages. Provide `--force` to bypass when users want to manage state without files present.
- Output modes: Add `--json` for machine-readable output and `--quiet` for script usage.
- Recursive scan: Add `--recursive` plus `--include/--exclude` globs, and support a `.curatorignore` file.
- Unify sort: Keep `scan --sort-by ...` as primary; keep `sort` as alias.
- Confirmations: For `delete`, prompt unless `--yes`. Add a `restore` command to recover from trash.
- Expired actions: Offer `expired --mark decide_later` to reset expired items automatically.

Reliability & Data Integrity
- State safety: Save a backup (`.curator_state.json.bak`) before writes; on corruption, warn and attempt restore.
- Timezone: Store ISO timestamps with timezone via `datetime.now().astimezone().isoformat()`.
- Trash collisions: When moving to trash, if name exists, append a numeric suffix ` (n)` before extension.
- Concurrency: Add a simple file lock during state updates to prevent races.

Internationalization & Sorting
- Case-insensitive sort: Use `str.casefold()` instead of `lower()` for better unicode handling.
- Natural sort: Optional `--natural` to sort numbers in names intuitively.
- Tag normalization: Optional `--normalize-tags lower|casefold|none`.

Performance
- Use `os.scandir()` to gather stat info efficiently.
- Large directories: Add progress/count output and `--limit` to page results.

Error Messaging & Exit Codes
- Consistent, user-friendly errors (avoid raw tracebacks for common cases).
- Non-zero exit codes on failures (e.g., 2 for not found, 64 for usage).

Features & Integration
- Rules engine CLI: `rules run|dry-run` operating on `curator_rules.json` to suggest/apply actions.
- Tag discovery: `tag --list` to list known tags and counts; `scan --filter-tag <tag>`.
- Flexible keep durations: `status <file> keep --days N` alongside fixed 90 days.

Developer Experience
- Logging: Replace prints with `logging` and a `--log-level` flag.
- Tooling: Add formatter/linter config sections in `pyproject.toml`.
- Tests: Add cases for unicode names, spaced repo paths, non-existent file error paths, and trash-name collisions; later add tests for `--json` and recursive/globs.
- Docs: Expand README with CLI quickstart and the new `data-curator` entry point; document `--json`, `--yes`, and restore.

Quick Wins (Implemented/Planned)
- Sorting uses `casefold()` for names.
- Timestamps include timezone.
- Trash moves handle name collisions by suffixing.
- CLI adds `--json` for `scan|sort|expired` outputs.
- CLI `delete` gains `--yes` confirmation.
- CLI pre-validates file existence with friendly errors; `status` and `tag` accept `--force` to bypass.
- CLI adds `restore <filename>` to move back from trash.

