from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import pathlib
import tempfile
import unittest

from sql_neatfmt import FormatOptions, format_sql
from sql_neatfmt.cli import main


FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class FixtureTests(unittest.TestCase):
    def test_fixtures(self) -> None:
        inputs = sorted(FIXTURES.glob("*.input.sql"))
        self.assertTrue(inputs)
        for input_path in inputs:
            case = input_path.name.removesuffix(".input.sql")
            expected_path = FIXTURES / f"{case}.expected.sql"
            dialect = case.split(".", 1)[0]
            with self.subTest(case=case):
                actual = format_sql(
                    input_path.read_text(encoding="utf-8"),
                    FormatOptions(dialect=dialect),
                )
                self.assertEqual(expected_path.read_text(encoding="utf-8"), actual)

    def test_fixtures_are_idempotent(self) -> None:
        expected_files = sorted(FIXTURES.glob("*.expected.sql"))
        self.assertTrue(expected_files)
        for expected_path in expected_files:
            case = expected_path.name.removesuffix(".expected.sql")
            dialect = case.split(".", 1)[0]
            expected = expected_path.read_text(encoding="utf-8")
            with self.subTest(case=case):
                self.assertEqual(expected, format_sql(expected, FormatOptions(dialect=dialect)))

    def test_keyword_case_lower(self) -> None:
        sql = "select a, b from t where x is not null and y = false;"
        self.assertEqual(
            "select a,\n"
            "       b\n"
            "from t\n"
            "where x is not null\n"
            "  and y = false;",
            format_sql(sql, FormatOptions(dialect="mysql", keyword_case="lower")),
        )


class CLITests(unittest.TestCase):
    def test_check_returns_zero_for_formatted_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "query.sql"
            path.write_text("SELECT a,\n       b\nFROM t;", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(["--dialect", "mysql", "--check", str(path)])

        self.assertEqual(0, result)
        self.assertEqual("", stderr.getvalue())

    def test_check_returns_one_without_rewriting_file(self) -> None:
        original = "select a, b from t;"
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "query.sql"
            path.write_text(original, encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                result = main(["--dialect", "mysql", "--check", str(path)])
            after = path.read_text(encoding="utf-8")

        self.assertEqual(1, result)
        self.assertEqual(original, after)
        self.assertIn("would reformat", stderr.getvalue())

    def test_diff_prints_unified_diff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "query.sql"
            path.write_text("select a, b from t;", encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                result = main(["--dialect", "mysql", "--diff", str(path)])

        diff = stdout.getvalue()
        self.assertEqual(1, result)
        self.assertIn("--- ", diff)
        self.assertIn("+++ ", diff)
        self.assertIn("+SELECT a,", diff)


if __name__ == "__main__":
    unittest.main()
