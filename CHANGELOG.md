# Changelog

## 0.1.6 - 2026-05-26

- Expand long derived-table `UNION` and `UNION ALL` queries instead of keeping
  them on a single `FROM (...)` line.
- Recognize MySQL `LOCATE()` as a function for keyword casing.

## 0.1.5 - 2026-05-15

- Improve long `CREATE TABLE` formatting with aligned column names, data types,
  `NOT NULL`, and default clauses.
- Format MySQL table options across lines with spaced assignments.
- Preserve MySQL `UNIQUE KEY` and `KEY ... USING BTREE` style for table
  constraints.

## 0.1.4 - 2026-05-08

- Add conservative `DROP TABLE` formatting so mixed SQL buffers do not fall
  back to unchanged output.
- Keep standalone line comments attached to long reformatted statements.
- Emit `AS` for literal projection aliases, such as constants in
  `INSERT ... SELECT` mappings.

## 0.1.3 - 2026-05-07

- Support common `--` line comments without falling back to unchanged SQL.
- Preserve blank lines between multiple formatted SQL statements.
- Document PyPI as the primary installation path.

## 0.1.2 - 2026-04-30

- Add review-corpus tooling for human approval of formatter style changes.
- Improve long subquery wrapping in Oracle `SET`, `EXISTS`, derived-table
  joins, and `PIVOT` queries.
- Improve DataGrip-like alignment for Oracle `MERGE`, projection aliases,
  PostgreSQL `RETURNING`, and `ON CONFLICT DO UPDATE SET`.
- Add broader MySQL, PostgreSQL, and Oracle review cases.

## 0.1.1 - 2026-04-30

- Add project-level agent guidelines in `AGENTS.md`.
- Add `--check` and `--diff` CLI modes for CI and review workflows.
- Add idempotence coverage for formatter fixtures.

## 0.1.0 - 2026-04-30

- Initial formatter CLI.
- SQLGlot-backed parsing for MySQL, PostgreSQL, and Oracle.
- Compact DataGrip-inspired layout for common SELECT, UPDATE, DELETE, INSERT,
  ALTER TABLE, CTE, join, scalar subquery, and returning/fetch cases.
- Default uppercase keywords with `--keyword-case lower` and
  `--no-uppercase-keywords` options.
- Length-aware `INSERT ... VALUES` wrapping for long column lists and value
  tuples.
