# Changelog

## 0.1.0 - 2026-04-30

- Initial formatter CLI.
- SQLGlot-backed parsing for MySQL, PostgreSQL, and Oracle.
- Compact DataGrip-inspired layout for common SELECT, UPDATE, DELETE, INSERT,
  ALTER TABLE, CTE, join, scalar subquery, and returning/fetch cases.
- Default uppercase keywords with `--keyword-case lower` and
  `--no-uppercase-keywords` options.
- Length-aware `INSERT ... VALUES` wrapping for long column lists and value
  tuples.
