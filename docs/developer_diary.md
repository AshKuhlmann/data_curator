# 2025-09-09

## Checklist

### Core Bugs & Fixes
- [ ] Restore path bug: `delete_file()` moves files to a per-directory `.<trash>` (`<dir>/.curator_trash/<name>`), but `handle_restore()` looks in repo root (`repo/.curator_trash/<name>`). Unify behavior:
  - [ ] Option A: Standardize on repo‑root trash dir; move to `os.path.join(repository_path, TRASH_DIR_NAME, relpath)` preserving subpaths.
  - [ ] Option B: Make `restore` search for the file in any `.curator_trash` beneath the repo (recursive) and restore it to the original location using stored metadata.
  - [ ] Persist delete context to state (last known original path and trash path) so restore works reliably even if multiple matches exist.
- [ ] State write atomicity: good use of temp + `os.replace`. Minor safety:
  - [ ] Ensure parent dir fsync on platforms that support it (already best‑effort). Consider using `pathlib.Path.replace` for clarity.
  - [ ] Handle disk‑full/permission errors with clearer messages and keep `.bak` intact.
- [ ] Schema versioning: present as `SCHEMA_VERSION = 1` and added tests. Add structured migration pipeline:
  - [ ] `migrations/` module with functions `migrate(v_from, state) -> (v_to, state)` and a loop until current.
  - [ ] On load, if `_schema_version` missing/older, migrate in‑memory and save.
- [ ] `open_file_location()` platform probe: current `elif os.uname().sysname == "Darwin"` is fine on POSIX, but `os.uname()` is not available on Windows. Since code already gates on `os.name == "nt"`, this is safe. Consider `sys.platform.startswith("darwin")` for clarity and to avoid `os.uname` import constraints in exotic runtimes.
 - [ ] Standardize handler error reporting: when core ops fail (`rename`, `delete`, `restore`), emit structured JSON errors and proper exit codes consistently (not just `print`).
 - [ ] Persist last action metadata (rename/delete contexts) in state to support a future `undo` command.

### UX & CLI
- [ ] Repository arg ergonomics:
  - [ ] Make `repository_path` optional (default to `.`) and add `-C/--repo PATH` that can be repeated (last wins) like Git.
  - [ ] Accept `~` and env var expansions; normalize to absolute paths early.
- [ ] Output modes:
  - [ ] Keep `--json` stable shapes; already includes `filtered_total` and `raw_total`. Document stable contracts and add a `version` field in JSON envelopes for future changes.
  - [ ] Add `--quiet` to more commands where user‑facing prints may appear (consistency audit).
  - [ ] Add `--color/--no-color` toggle (no-op for JSON) to improve TTY UX.
  - [ ] Ensure stdout vs stderr separation: data to stdout; human/logs to stderr; JSON mode writes only JSON to stdout.
- [ ] Sorting & filtering:
  - [ ] Natural sort option (`--natural`) for humanized name sorting when not using size/date.
  - [ ] Add `--filter-tag TAG` to filter by exact tag and `--filter-regex` to complement substring search.
  - [ ] Support `--since/--until` filters for mtime ranges.
  - [ ] Support `--sort-by created|accessed` where available; degrade gracefully when unsupported.
- [ ] Scanning controls:
  - [ ] `.curatorignore` is supported; document pattern semantics (path vs basename, `**/` behavior) with examples and tests.
  - [ ] Consider `--hidden` to include dotfiles; currently hidden files/dirs are skipped.
  - [ ] Add `--exclude-dir DIR` (repeatable) to skip whole directories without requiring complex globs.
- [ ] Status semantics:
  - [ ] `keep_90_days` correctly maps to `keep` with `days=90`. Mark `keep_90_days` as deprecated in docs; emit a warning when used.
  - [ ] Permit explicit `--until YYYY-MM-DD` in addition to `--days` for `keep`.
  - [ ] Optional `--note` freeform string per item (persist in state) to record why decisions were made.
- [ ] Batch UX:
  - [ ] For `status-batch` and `tag-batch`, add `--stop-on-error` to halt early for strict workflows.
  - [ ] Echo a compact summary in non‑JSON mode (updated/failed counts with examples).
- [ ] Safety prompts:
  - [ ] `delete` correctly prompts unless `--yes`. Add `--dry-run` to print target path and trash destination.
  - [ ] For `rules apply delete`, add optional `--yes` or `--dry-run` gate.
- [ ] CLI help:
  - [ ] Add examples for every subcommand in `argparse` epilog.
  - [ ] Provide shell completion stubs (bash/zsh/fish) via `argcomplete` or static generation.
 - [ ] Validate `status` values against an allowed set; reject unknown values with exit code 3 and JSON error.
 - [ ] Add `open`/`reveal` command to expose `open_file_location()` for convenience.
 - [ ] Add trash management commands: `trash list`, `trash prune --older N`, and `restore --all`.
 - [ ] Add `list --status <status>` to list curated items (not just pending) and support status filtering.
 - [ ] Add `init` command to create a baseline `.curatorignore` and recommended `.gitignore` entries.
 - [ ] Audit and document exit code semantics across all commands; ensure consistent 0/1/2/3 usage.

### Data Integrity & Concurrency
- [ ] State locking: cross‑platform lock file is good. Add:
  - [ ] Lock acquisition timeout (env or flag) with friendly error when another process holds the lock.
  - [ ] Write‑skew prevention: reload state on write failure and retry small N times.
- [ ] State bloat:
  - [ ] Add `gc` command to prune entries for files that no longer exist and have permanent decisions.
  - [ ] Optional `--compact` to sort keys and remove nulls for readability.
- [ ] Backups:
  - [ ] Rotate `.curator_state.json.bak.N` with cap (e.g., last 3 writes) to increase recovery options.
 - [ ] Configurable state and trash locations via config/env (e.g., `.data_curator/` root); provide migration helpers.
 - [ ] State import/export commands to move state between machines; add `state diff` between backups.

### Performance & Scalability
- [ ] Use `os.scandir()` when gathering stats for `date/size` sorts to avoid repeated syscalls.
- [ ] Paginate at the scan source (yield and stop at `limit`) to avoid building large lists first.
- [ ] Consider caching stat results during a single command run; invalidate by mtime.
- [ ] For very large repos, add a `--progress` counter and optional rate‑limited progress prints.
 - [ ] Add `--json-lines` streaming output for `scan/sort` to avoid buffering entire result sets.

### Rules Engine
- [ ] CLI coverage already present (dry‑run/apply). Expand capabilities:
  - [ ] Add `move` action (to a target subfolder) and `rename` action with templates (e.g., `"{stem}-archived{suffix}"`).
  - [ ] Tag action supports multiple tags: allow list in `action_value` or `{ "add": [..], "remove": [..] }`.
  - [ ] Condition operators: add `regex`, `not`, combinations with `any/all` groups.
  - [ ] File attributes: `size`, `mtime`, `path contains`, `depth`, `is_binary` (simple sniff).
  - [ ] Dry‑run output should include the would‑be destination paths.
  - [ ] Add rule validation command `rules validate` with schema errors surfaced.
  - [ ] Add `rules test --file <path>` to show the first matching rule/action for a single file.
  - [ ] Add `rules metrics` to summarize matches per rule for tuning.
  - [ ] Define and enforce a JSON Schema for rules; validate on load with detailed error locations.

### Testing
- [ ] Add E2E tests for the trash/restore mismatch to prevent regressions.
- [ ] Tests for `.curatorignore` path patterns vs basename patterns, including `**/` behavior.
- [ ] Windows paths: simulate with `pathlib.PureWindowsPath` where possible; CI matrix on Windows runner.
- [ ] Fuzz tests for batch inputs (empty lines, duplicated names, unicode, very long names).
- [ ] Property tests for `_unique_path()` to ensure no collisions across concurrent creates (use tmp + threads).
- [ ] Migration tests: start from older schema snapshots, run load+migrate, assert final state.
- [ ] JSON contract tests: golden samples for `scan/sort/expired` with paging and filters.
 - [ ] Measure coverage and enforce a CI threshold (e.g., 90%); produce local HTML reports.
 - [ ] Verify clean stdout/stderr separation across commands and modes.
 - [ ] Handle KeyboardInterrupt gracefully; ensure no partial state writes; add tests.
 - [ ] Multi-process lock contention test to complement unit locking checks.
 - [ ] Golden-file tests for CLI help/usage to catch accidental regressions.
 - [ ] Exit code consistency tests for all commands (success, invalid input, not found).

### Documentation
- [ ] Expand README quickstart with a minimal workflow: scan → decide → tag → delete/restore → expired reset.
- [ ] Document state JSON shape and schema version, including `keep_days`, `expiry_date`, and timezone semantics.
- [ ] Dedicated page for ignore patterns with concrete examples and gotchas.
- [ ] Troubleshooting page for common errors (permission denied, lock held, path not found) and how to recover.
- [ ] Contributing: note required Python version, Poetry usage, and the local pre‑commit workflow.
 - [ ] Full workflow walkthrough in README: scan → decide → tag → delete → restore → expired reset.
 - [ ] “Statuses and lifecycle” page/section explaining how each status appears in scans.
 - [ ] Dedicated “Trash Management” page (list, prune, restore behavior, collision strategy, locations).
 - [ ] “Configuration” page: defaults, config files, env vars, recommended `.gitignore` entries.
 - [ ] Add a short “Glossary” of core terms (repository, state, trash, expired, rules).

### Developer Experience & Tooling
- [ ] Logging: replace `print` with `logging` and a `--log-level` flag; ensure JSON mode remains clean (no extra logs to stdout).
- [ ] Type safety: add explicit `TypedDict`/`dataclass` for state entries and rule structures; enable stricter mypy flags for the package (e.g., `disallow_untyped_defs`).
- [ ] Ruff rules: adopt a curated rule set (e.g., `E`, `F`, `I`, `UP`, `B`, `SIM`) and autofix imports.
- [ ] Pre-commit hook (git) to run formatters quickly on changed files; current `scripts/pre-commit` is a good CI gate.
- [ ] Add `make` targets or `task` runner equivalents (`make test`, `make lint`, `make fmt`).
 - [ ] Publish `py.typed` to mark the package as typed for downstream projects.
 - [ ] Enrich `pyproject.toml`: add `project.urls`, classifiers, keywords, license metadata, and long description.
 - [ ] Centralize tool config in `pyproject.toml` (`tool.ruff`, `tool.black`, `tool.mypy`), including excludes.
 - [ ] Document and support `pipx install data-curator` for safe CLI installs.
 - [ ] Offer optional extras (e.g., `tui`) for future UI dependencies.

### CI/CD
 - [ ] Expand CI matrix to Python 3.11–3.13 across Ubuntu/macOS/Windows; cache Poetry and wheels.
 - [ ] Add `poetry lock --check` step to keep lockfile in sync.
 - [ ] Enable workflow concurrency to cancel superseded runs.
 - [ ] Release pipeline: tag → build sdist/wheel → publish to PyPI (with provenance where possible).
 - [ ] Integrate coverage reporting in PRs (Codecov/Coveralls) with status checks.

### Platform Compatibility
- [ ] Filesystems: ensure behavior on case‑insensitive FS (macOS default) is well‑tested. Consider case‑folded comparisons already used in scanning logic; document implications.
- [ ] Unicode: add tests for NFC/NFD normalization (macOS) and ensure tags/filenames round‑trip as expected.
- [ ] Large files: exercise size sort and operations on multi‑GiB files (stat only).
 - [ ] Windows long-path guidance (opt-in `\\?\\` prefix) and tests where feasible.
 - [ ] Document behavior/limitations on network shares (SMB/NFS) for locks.
 - [ ] Large-directory stress tests (100k+ files) and doc guidance for paging and JSON-lines.
 - [ ] Verify macOS unicode normalization (NFD) handling for filenames; ensure round-trip on rename/tag.

### Backward Compatibility & Migrations
- [ ] Maintain compatibility for older states (no `_schema_version`), migrate forward on write.
- [ ] Provide a `state migrate --dry-run` command that prints planned changes before writing.
- [ ] Provide a `state verify` command to validate integrity (e.g., keys are strings, known statuses only).

### Security & Safety
- [ ] Dry‑run for destructive actions (`delete`, `rules apply delete`).
- [ ] Guard rails on `--include/--exclude` that would match nothing or everything; warn in TTY mode.
- [ ] When moving files, handle permission errors gracefully and avoid partial state updates (write state after successful FS ops).
- [ ] Avoid following symlinks during scans/deletes by default; add `--follow-symlinks` opt‑in.

### Nice‑to‑Haves
- [ ] Optional TUI (text UI) using `textual`/`rich` to step through items with keybindings, using the same core.
- [ ] Export reports: `scan --json |` helpers and `report` subcommand to summarize by status/tag/age.
- [ ] Config file support (toml) for default flags per repo (e.g., recursive include patterns).

---
- Expired listing returns `details` with `days_overdue`. `--mark-decide-later` updates are idempotent and report updated/expired pairs in JSON.
- The restore path bug is user‑visible today: deleting `subdir/file` puts it in `subdir/.curator_trash/file`, but `restore subdir/file` can’t find it. Recommend addressing before next release.
