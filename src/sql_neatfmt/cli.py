from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, version
import pathlib
import sys

from .formatter import FormatOptions, format_sql


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sql-neatfmt",
        description="Format SQL in a compact style.",
    )
    parser.add_argument("files", metavar="FILE", nargs="*", help="input SQL file, or '-' for stdin")
    parser.add_argument(
        "-d",
        "--dialect",
        default="mysql",
        help="SQL dialect understood by SQLGlot, e.g. mysql, postgres, oracle",
    )
    parser.add_argument(
        "--keyword-case",
        choices=("upper", "lower"),
        default="upper",
        help="keyword case to emit; defaults to upper",
    )
    parser.add_argument(
        "--no-uppercase-keywords",
        action="store_const",
        const="lower",
        dest="keyword_case",
        help="alias for --keyword-case lower",
    )
    parser.add_argument("-o", "--output", metavar="FILE", help="write formatted SQL to FILE")
    parser.add_argument("--fix", action="store_true", help="update input files in place")
    parser.add_argument("--version", action="store_true", help="show version and exit")
    return parser


def read_input(paths: list[str]) -> str:
    if not paths:
        return sys.stdin.read()

    chunks: list[str] = []
    for path in paths:
        if path == "-":
            chunks.append(sys.stdin.read())
        else:
            chunks.append(pathlib.Path(path).read_text(encoding="utf-8"))
    return "\n".join(chunks)


def write_output(sql: str, path: str | None) -> None:
    if path:
        pathlib.Path(path).write_text(sql, encoding="utf-8")
    else:
        sys.stdout.write(sql)


def fix_files(paths: list[str], options: FormatOptions) -> int:
    if not paths:
        sys.stderr.write("sql-neatfmt: --fix requires at least one file\n")
        return 2
    if "-" in paths:
        sys.stderr.write("sql-neatfmt: --fix cannot be used with stdin\n")
        return 2

    for path in paths:
        file = pathlib.Path(path)
        file.write_text(format_sql(file.read_text(encoding="utf-8"), options), encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        try:
            package_version = version("sql-neatfmt")
        except PackageNotFoundError:
            package_version = "0.0.0+unknown"
        sys.stdout.write(f"sql-neatfmt {package_version}\n")
        return 0
    if args.fix and args.output:
        parser.error("--fix cannot be used with --output")

    options = FormatOptions(dialect=args.dialect, keyword_case=args.keyword_case)
    if args.fix:
        return fix_files(args.files, options)

    write_output(format_sql(read_input(args.files), options), args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
