# AGENTS.md

## Project Scope

`sql-neatfmt` is a Python CLI formatter for SQL. It uses SQLGlot for
dialect-aware parsing and applies a compact, DataGrip-inspired layout.

The formatter must be conservative: if parsing fails, input is templated, or a
case is unsafe to transform, return the original SQL unchanged.

## Core Principles

- Prefer simple, direct code over clever abstractions.
- Do not add layers or files unless they solve a current problem.
- Diagnose the root cause before changing formatter behavior.
- Do not stack speculative fixes. After two failed attempts, stop patching and
  add diagnosis or fixtures first.
- Formatting must not change SQL meaning.

## Architecture

- `src/sql_neatfmt/cli.py` owns argument parsing, file I/O, exit codes, and CLI
  behavior. Keep it thin.
- `src/sql_neatfmt/formatter.py` owns SQL formatting rules.
- SQLGlot AST is the source of structural truth. Prefer AST-based decisions over
  regex/string parsing.
- Regex/string helpers are acceptable only for narrow, top-level layout tasks
  where SQLGlot does not expose a useful structure.
- Keep `FormatOptions` as the explicit configuration boundary.

## Formatting Rules

- Default keyword case is uppercase.
- Preserve string literals and quoted identifiers.
- Preserve trailing semicolon behavior.
- Prefer compact readable SQL over blocky output.
- Keep short derived tables, scalar subqueries, and `EXISTS` predicates inline;
  wrap them only when the full containing line exceeds the configured width.
- `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `SET`, `RETURNING`, and similar
  clause layouts must be covered by fixtures before behavior changes.
- New layout rules must be idempotent.
- If a dialect feature cannot be formatted confidently, pass it through rather
  than producing a partially formatted query.

## Review Corpus

- `review-cases/{dialect}/` contains broader human-review samples. Use it to
  reproduce style gaps before changing formatter behavior.
- `review-output/` is generated local output and must stay untracked.
- Regenerate review output with:

```sh
uv run python scripts/render_review.py review-cases/mysql review-output/mysql
uv run python scripts/render_review.py review-cases/postgres review-output/postgres
uv run python scripts/render_review.py review-cases/oracle review-output/oracle
```

- Promote only stable, reviewed behavior into `tests/fixtures/`.
- Use `scripts/accept_case.py` when accepting a review sample as a regression
  fixture.

## Dialect Policy

- Dialect names follow SQLGlot where possible: `mysql`, `postgres`, `oracle`,
  etc.
- Do not claim dialect support without fixtures.
- For dialect-specific behavior, add fixtures for that dialect.
- For shared behavior, prefer adding fixtures across MySQL, Postgres, and Oracle
  when the syntax is valid in all three.

## Tests

Run before committing:

```sh
uv run python -m unittest discover -s tests
uv build --no-sources
```

For formatter layout changes, also check generated review output is idempotent.

Fixture naming:

```text
tests/fixtures/{dialect}.{case}.input.sql
tests/fixtures/{dialect}.{case}.expected.sql
```

When fixing a formatting bug:

- Add or update the failing fixture first.
- Confirm the fixture fails before changing formatter code.
- Keep expected SQL readable and intentional.
- Add CLI tests when changing flags, stdin/stdout behavior, `--fix`, output
  files, or exit codes.

## Python Style

- Target Python 3.11+.
- Use `from __future__ import annotations`.
- Use type hints for public functions and non-trivial helpers.
- Prefer `pathlib` for filesystem paths.
- Keep side effects at CLI boundaries.
- Avoid broad `except` except at explicit safety boundaries such as parsing.
- Do not silently swallow formatter bugs inside core logic.
- Use small helpers named after what they compute.
- Add comments only for non-obvious logic.

## User-Facing Changes

Update docs in the same change when modifying:

- CLI flags
- default formatting behavior
- installation instructions
- release workflow
- supported dialect claims

Update `CHANGELOG.md` for released behavior changes.

## Release

Before release:

```sh
uv run python -m unittest discover -s tests
uv build --no-sources
```

Release through GitHub Actions / PyPI Trusted Publishing. Do not publish local
artifacts that were not built from the intended commit.

## Do Not

- Do not rewrite formatter architecture for cosmetic reasons.
- Do not add compatibility shims for removed behavior.
- Do not change editor configs from this repo.
- Do not mark unsupported SQL as formatted if the output is uncertain.
