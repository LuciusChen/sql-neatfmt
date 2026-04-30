from __future__ import annotations

import argparse
import pathlib


FIXTURES = pathlib.Path(__file__).resolve().parents[1] / "tests" / "fixtures"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Accept a reviewed SQL case as a fixture.")
    parser.add_argument("dialect", help="fixture dialect prefix, e.g. mysql")
    parser.add_argument("name", help="fixture case name, e.g. select_join")
    parser.add_argument("input_sql", type=pathlib.Path, help="original SQL case")
    parser.add_argument("expected_sql", type=pathlib.Path, help="reviewed formatted SQL")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    FIXTURES.mkdir(parents=True, exist_ok=True)

    prefix = f"{args.dialect}.{args.name}"
    input_path = FIXTURES / f"{prefix}.input.sql"
    expected_path = FIXTURES / f"{prefix}.expected.sql"

    input_path.write_text(args.input_sql.read_text(encoding="utf-8"), encoding="utf-8")
    expected_path.write_text(args.expected_sql.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"accepted {prefix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
