# Data Curator — Documentation Compendium

This single document condenses the current documentation into a concise, navigable summary for contributors and stakeholders.

## Table of Contents
- Project Overview
- Repository Structure
- Core Components
- CLI Summary
- Rules Engine
- Development Workflow
- Quality Gates
- Devlog Highlights (What’s Done)
- User Feedback Highlights
- Roadmap (Plan)
- Troubleshooting

## Project Overview
Data Curator helps you curate files in a directory one at a time, tracking decisions in a local JSON state so sessions can resume. The project provides a CLI (argparse) built on shared core functions.

Requires Python >= 3.11. Dependency management via Poetry.

## Repository Structure
- `data_curator_app/`: Application package
  - `curator_core.py`: State, scanning, tags, file ops (SSOT)
  - `cli.py`: CLI entry and handlers
  - `rules_engine.py`: Simple rules DSL and evaluator
- `tests/`: Pytest suite
- `scripts/pre-commit`: Local CI gate (format/lint/type/test/install)
- `docs/`: Documentation and planning notes
- `pyproject.toml` / `poetry.lock`: Project metadata and deps
- `README.md`: Quickstart and usage
- `LICENSE`: GPLv3

Common files created in curated folders:
- `.curator_state.json`: Per-repo state (status, tags, timestamps, optional expiry)
- `.curator_trash/`: Safe “trash” for soft-deletes
- `.curatorignore` (optional): Ignore patterns for scans

## Core Components
1) Core (`curator_core.py`)
- Load/save JSON state; resilient backup/restore planned
- Scan with include/exclude globs, hidden-file rules, `.curatorignore`
- Status and tagging helpers
- File ops: rename, delete→trash (unique suffix), restore, expired reset
- Cross-platform helpers (e.g., open location)

2) CLI (`cli.py`)
- Thin wrapper: parse args, validate, delegate to core
- Supports JSON and quiet modes for scripting

3) Rules (`rules_engine.py`)
- Evaluate simple conditions on file attributes; return first matching action
- Basis for future CLI automation hooks

## CLI Summary
Installed entry point: `data-curator`

Key subcommands (selection):
- `scan` / `sort` with filtering, include/exclude globs, recursive, JSON, paging
- `status` and `tag` (single and batch variants) with `--force`, JSON, quiet
- `rename`, `delete --yes`, `restore`
- `expired --mark-decide-later`

Conventions:
- Sorting: name (casefold), date (mtime), size (bytes)
- Exit codes standardized for common error cases (in progress)

## Rules Engine
- Inputs: `curator_rules.json`
- Conditions: `extension`, `filename`, `age_days`; operators like `is`, `contains`, `gt`, etc.
- Actions: e.g., `delete`, `add_tag`
- Planned: CLI `rules dry-run|apply` with JSON report

## Development Workflow
- Setup:
  - `pip install poetry`
  - `poetry install`
- Run:
  - CLI: `poetry run data-curator /path scan --json`

## Quality Gates
- Always run `./scripts/pre-commit` before a PR. It runs:
  - `black --check .`
  - `ruff check .`
  - `mypy data_curator_app`
  - `pytest -q`
  - `python -m pip install .`

## Devlog Highlights (What’s Done)
- Sorting uses `casefold()`; timestamps include timezone
- Trash moves collision-safe via suffixing
- CLI JSON output for `scan|sort|expired`; `delete --yes`
- Pre-validation with friendly errors; `--force` for certain commands
- `restore` command to recover from trash

## User Feedback Highlights
- Need robust CLI with JSON and batch operations
- Improve state and rules file locations/configurability
- Expand previews and add rules dry-run
- Add rules documentation and examples

## Roadmap (Plan)
Near term:
- JSON totals for filtered/paged results
- Edge-case patterns; paging polish; quiet-mode audit
- Batch from file/stdin; standardized error JSON and exit codes
- Rules CLI: `dry-run` and `apply` with JSON
- Expired details and mark-decide-later idempotency

Medium term:
- Config defaults; shell completion; restore discovery UX
- Performance benchmarks and optional concurrency
- Cross-platform path/hidden/trash behavior; logging options; JSON schema versioning

Longer term:
- Plugin hooks; richer rules DSL; opt-in telemetry; packaging across ecosystems

Documentation tasks:
- Expand README examples (paging, batch, JSON, exit codes)
- Add `docs/examples/` and troubleshooting guide

## Troubleshooting
- Type errors: `poetry run mypy data_curator_app`
- Lint/style: `poetry run ruff check .` and `poetry run black .`
- Tests: `poetry run pytest -q`
- Packaging sanity: `python -m pip install .`

---
Status note: This compendium reflects the current `docs/` set (`project_structure`, `project_organization.md`, `devlog.md`, `plan.md`, `user_feedback.md`) in condensed form.
