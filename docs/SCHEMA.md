State Schema

Overview
- The state file is stored at `.curator_state.json` in each curated repository.
- It is a single JSON object (dictionary) keyed by filename with per‑file metadata.
- A reserved top‑level key `_schema_version` indicates the version of the state
  schema written by the current application. This enables forward migrations.

Schema Version
- Key: `_schema_version`
- Type: integer
- Semantics:
  - Present in all state files written by this version of the app.
  - The writer sets this value to the current version (`1`).
  - Readers must tolerate missing values (older files) and unknown higher values
    (forward compatibility) — the current implementation ignores the value when
    reading but always writes the current version when saving.

Per‑File Entry
- Key: `<relative filename>` (string)
- Value: object with fields:
  - `status` (string): one of
    - `decide_later` — default queue state
    - `keep` — temporary keep; see `keep_days` and `expiry_date`
    - `keep_forever` — permanent keep
    - `deleted` — moved to curator trash
    - `renamed` — file was renamed
    - Legacy: `keep_90_days` (accepted for backward compatibility; normalized
      to `keep` on update)
  - `tags` (array of string, optional): user‑assigned tags
  - `last_updated` (ISO8601 string, optional): set by updates
  - `keep_days` (integer, optional): number of days for temporary keeps
  - `expiry_date` (ISO8601 string, optional): calculated from `keep_days`

Reserved Keys
- Any top‑level keys beginning with `_` are reserved for non‑file metadata.
  Current set: `_schema_version`.

Compatibility Notes
- Older state files without `_schema_version` are fully supported.
- On the next save, the application will write `_schema_version: 1`.
- Scans and expired checks ignore non‑file entries and are robust to malformed
  per‑file entries.

