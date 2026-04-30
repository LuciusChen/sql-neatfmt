from __future__ import annotations

import argparse
import pathlib

from sql_neatfmt import FormatOptions, format_sql


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render review SQL cases.")
    parser.add_argument("input_dir", type=pathlib.Path, help="directory containing .sql review cases")
    parser.add_argument("output_dir", type=pathlib.Path, help="directory for formatted output")
    parser.add_argument(
        "-d",
        "--dialect",
        help="SQL dialect; defaults to the input directory name",
    )
    parser.add_argument(
        "--keyword-case",
        choices=("upper", "lower"),
        default="upper",
        help="keyword case to emit; defaults to upper",
    )
    return parser


def render_cases(input_dir: pathlib.Path, output_dir: pathlib.Path, options: FormatOptions) -> int:
    files = sorted(input_dir.glob("*.sql"))
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in files:
        formatted = format_sql(path.read_text(encoding="utf-8"), options)
        (output_dir / path.name).write_text(formatted, encoding="utf-8")

    return len(files)


def main() -> int:
    args = build_parser().parse_args()
    dialect = args.dialect or args.input_dir.name
    count = render_cases(
        args.input_dir,
        args.output_dir,
        FormatOptions(dialect=dialect, keyword_case=args.keyword_case),
    )
    print(f"rendered {count} case(s) from {args.input_dir} to {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
