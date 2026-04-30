# sql-neatfmt

`sql-neatfmt` is a compact SQL formatter designed for editor use.
It uses SQLGlot for dialect-aware parsing and owns the final layout rules.

The formatter intentionally favors readable query editing:

```sql
SELECT a.id,
       a.name,
       b.code code_name
FROM table_a a
         LEFT JOIN table_b b
           ON a.id = b.a_id
          AND b.deleted = 0
WHERE a.status = 1
  AND a.created_at >= DATE '2026-04-01'
GROUP BY a.id
ORDER BY a.id DESC;
```

## Usage

```sh
sql-neatfmt --dialect mysql < query.sql
sql-neatfmt --dialect postgres query.sql
sql-neatfmt --dialect oracle --fix query.sql
sql-neatfmt --dialect mysql --keyword-case lower query.sql
sql-neatfmt --dialect mysql --check query.sql
sql-neatfmt --dialect mysql --diff query.sql
```

Keywords are uppercased by default. Use `--keyword-case lower` or
`--no-uppercase-keywords` to emit lowercase keywords instead.

Use `--check` in CI or editor hooks to fail when SQL would be reformatted.
Use `--diff` to print a unified diff without modifying files.

## Review Corpus

Broader style samples live under `review-cases/{dialect}/`. These are intended
for human review before a style rule is promoted into `tests/fixtures/`.

Render the current formatter output locally:

```sh
uv run python scripts/render_review.py review-cases/mysql review-output/mysql
uv run python scripts/render_review.py review-cases/postgres review-output/postgres
uv run python scripts/render_review.py review-cases/oracle review-output/oracle
```

`review-output/` is ignored by Git. After a rendered case has been reviewed and
accepted, promote it to a regression fixture:

```sh
uv run python scripts/accept_case.py oracle pivot_subquery \
  review-cases/oracle/015-pivot.sql \
  review-output/oracle/015-pivot.sql
```

## Installation

Install from a local checkout:

```sh
uv tool install --from ~/repos/sql-neatfmt sql-neatfmt
```

Install from a Git checkout:

```sh
uv tool install git+https://github.com/LuciusChen/sql-neatfmt
```

After publishing to PyPI:

```sh
uv tool install sql-neatfmt
```

Build release artifacts:

```sh
uv build --no-sources
```

Publish to PyPI from GitHub Actions:

1. Create a PyPI pending trusted publisher for `sql-neatfmt`.
2. Use owner `LuciusChen`, repository `sql-neatfmt`, workflow
   `publish.yml`, and environment `pypi`.
3. Run the `Publish` workflow from GitHub Actions, or publish a GitHub release.

Publish from this checkout after setting a PyPI token:

```sh
uv publish --check-url https://pypi.org/simple/
```

Supported initial dialect names follow SQLGlot: `mysql`, `postgres`, `oracle`,
`sqlite`, `tsql`, and others accepted by SQLGlot.

## Scope

This is intentionally conservative. Parse failures, comments, and templated SQL
are returned unchanged rather than risk corrupting the query.
