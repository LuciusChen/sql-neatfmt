from __future__ import annotations

import pathlib
import unittest

from sql_neatfmt import FormatOptions, format_sql


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


if __name__ == "__main__":
    unittest.main()
