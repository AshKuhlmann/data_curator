# Project Improvement Plan

This plan captures the next set of improvements we intend to make to the CLI and core, grouped by priority. We will continue to work test-first (add failing tests, then implement) and document user-facing behavior in README and docs.

## Near-Term (next 1–2 iterations)

- JSON totals: add filtered vs raw totals in JSON envelopes when filters/paging are used.
- Pattern edge cases: expand tests for `--include/--exclude` glob nuances (leading slashes, case-insensitive filesystems, dotfiles, Unicode).
- Paging polish: verify `--limit/--offset` on large trees; add tests for boundary conditions (offset beyond end, zero/negative handling).
- Batch from file/stdin: support `--from-file` and stdin for `status-batch`/`tag-batch`; aggregated JSON results; exit code semantics on partial failure.
- Rules engine CLI: add `rules dry-run` and `rules apply` with JSON report (matched, actions, diffs); cover with tests.
- Expired reporting: add `--json` details for why a file is expired; implement `expired --mark-decide-later` already planned with tests for idempotency.
- Error model: finalize structured JSON errors `{ "error", "code" }`; audit exit codes (2 for not found, 3 for invalid input, 4 for partial failure in batch).
- Quiet mode audit: ensure `--quiet` suppresses non-essential output across all subcommands; add tests.

## Medium-Term (usability and depth)

- Config file: support project/user config (e.g., `.curatorrc` or `pyproject.tool.data_curator`) for defaults: ignore patterns, default sort, JSON mode.
- Shell completion: generate completion scripts for bash/zsh/fish; add `completion` subcommand.
- Restore UX: `restore` discovery of recently trashed items with `--list` and filters; JSON output with provenance info.
- Performance: benchmark scan/sort on large trees; optional concurrency for metadata reads; guard with `--max-workers` and deterministic ordering.
- Cross-platform: verify Windows paths, case handling, hidden files, and trash behavior; add targeted tests.
- Logging: structured logs with levels; `--log-level` and `--log-json` for machine pipelines (quiet remains separate from logging).
- JSON schema: version the JSON output (`meta.schema_version`); publish minimal schema docs.
- CLI API stability: declare stability levels per command; deprecation policy with warnings/tests.

## Longer-Term (extensibility and ecosystem)

- Plugin hooks: allow file-type analyzers/extractors (e.g., images, PDFs) via entry points; include sample plugin and tests.
- Rules language: richer DSL for rules (date math, size, path globs, tags, status) with YAML/JSON rule sets and validation.
- Telemetry (opt-in): anonymous command/flag usage to guide UX; clearly documented and disabled by default.
- Packaging: publish `pipx`-friendly package; optional Homebrew tap. Explore Windows package (winget/choco) and Linux (snap/appimage) if demand exists.

## Documentation

- README usage: expand with paging, batch, and JSON examples; call out exit code table.
- Devlog: summarize implemented “quick wins” and note upcoming breaking changes, if any.
- Examples: add a `docs/examples/` folder with sample command transcripts and JSON.
- Troubleshooting: common errors, exit codes, and remedies.

## Testing & CI

- Coverage gates: aim for >90% on core and CLI; add badge.
- Matrix CI: Linux, macOS, Windows; py311/py312.
- Fuzzing: light fuzz for include/exclude and path normalization.
- Large-tree tests: synthetic generator to stress paging and sorting determinism.

## Guardrails & Safety

- Dry-run flags: add `--dry-run` to all destructive operations (delete/rename/batch/apply) with clear JSON diffs.
- Trash safety: collision strategy already unique-suffixed; add tests for race-like scenarios; cap trash size and warn when exceeding threshold.
- Validation: preflight for non-existent inputs in batch; partial failure JSON with per-item codes.

## Developer Experience

- Error messages: consistent, actionable messages with remediation hints; unify style guide.
- Internal APIs: reduce coupling between CLI and core; define stable interfaces.
- Local tooling: pre-commit hooks for formatting/typing; fast lint target.

---

Execution approach: continue TDD, keep changes incremental, avoid breaking CLI behaviors without deprecation, and update docs alongside code. Open items will be moved to the devlog as they land.

