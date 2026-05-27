from __future__ import annotations

from dataclasses import dataclass
import logging
import re
from typing import Literal

import sqlglot
from sqlglot import exp


KeywordCase = Literal["upper", "lower"]


@dataclass(frozen=True)
class FormatOptions:
    dialect: str = "mysql"
    keyword_case: KeywordCase = "upper"
    select_indent: int = len("select ")
    condition_indent: int = 2
    join_indent: int = len("from ") + 4
    join_condition_indent: int = 2
    update_join_indent: int = 4
    update_join_condition_indent: int = 4
    update_join_continuation_indent: int = 8
    alter_action_indent: int = 2
    short_query_max_width: int = 120


@dataclass(frozen=True)
class LineComment:
    text: str
    leading: str
    inline_anchor: str | None = None
    following_anchor: str | None = None


@dataclass(frozen=True)
class ColumnDefinitionLayout:
    name: str
    kind: str
    constraints: list[str]
    has_not_null: bool


TEMPLATE_RE = re.compile(
    r"</?(select|insert|update|delete|include|if|where|foreach|choose|when|otherwise|trim|set)\b|[#][$]?\{",
    re.IGNORECASE,
)
BLOCK_COMMENT_RE = re.compile(r"/\*")
ORACLE_UNSUPPORTED_RE = re.compile(r"\b(connect\s+by|start\s+with)\b", re.IGNORECASE)
SQL_KEYWORDS = {
    "add",
    "all",
    "alter",
    "and",
    "auto_increment",
    "as",
    "asc",
    "between",
    "bigint",
    "boolean",
    "by",
    "case",
    "cast",
    "char",
    "charset",
    "check",
    "clob",
    "column",
    "columns",
    "conflict",
    "constraint",
    "comment",
    "create",
    "cross",
    "current",
    "current_timestamp",
    "date",
    "datetime",
    "default",
    "delete",
    "desc",
    "decimal",
    "distinct",
    "do",
    "drop",
    "duplicate",
    "else",
    "end",
    "engine",
    "escape",
    "exists",
    "false",
    "fetch",
    "following",
    "for",
    "foreign",
    "first",
    "from",
    "full",
    "generated",
    "group",
    "having",
    "identity",
    "in",
    "index",
    "inner",
    "insert",
    "int",
    "integer",
    "into",
    "is",
    "join",
    "json",
    "jsonb",
    "key",
    "lateral",
    "left",
    "like",
    "limit",
    "matched",
    "merge",
    "modify",
    "not",
    "null",
    "number",
    "numeric",
    "offset",
    "only",
    "on",
    "or",
    "order",
    "outer",
    "over",
    "partition",
    "path",
    "pivot",
    "preceding",
    "primary",
    "recursive",
    "references",
    "returning",
    "right",
    "row",
    "rows",
    "select",
    "set",
    "smallint",
    "sysdate",
    "table",
    "then",
    "timestamp",
    "timestamptz",
    "tinyint",
    "true",
    "union",
    "unique",
    "unbounded",
    "unpivot",
    "update",
    "using",
    "values",
    "varchar",
    "varchar2",
    "when",
    "where",
    "with",
}
SQL_FUNCTIONS = {
    "avg",
    "add_months",
    "coalesce",
    "concat",
    "concat_ws",
    "count",
    "date_format",
    "decode",
    "dense_rank",
    "extract",
    "group_concat",
    "ifnull",
    "json_extract",
    "json_table",
    "json_unquote",
    "jsonb_array_elements",
    "jsonb_to_recordset",
    "lag",
    "lead",
    "length",
    "locate",
    "lower",
    "max",
    "min",
    "now",
    "nvl",
    "nvl2",
    "rank",
    "regexp_substr",
    "row_number",
    "round",
    "substr",
    "substring",
    "sum",
    "sys_connect_by_path",
    "to_char",
    "to_date",
    "to_number",
    "to_timestamp",
    "trunc",
    "upper",
    "values",
}


def format_sql(sql: str, options: FormatOptions | None = None) -> str:
    options = options or FormatOptions()
    stripped_sql, line_comments = strip_line_comments(sql)
    if unsafe_input(stripped_sql, options):
        return sql

    trailing_newline = sql.endswith("\n")
    try:
        statements = parse_sql(stripped_sql, options)
    except Exception:
        repaired_sql = repair_missing_join_keywords(stripped_sql)
        if repaired_sql == stripped_sql:
            return sql
        try:
            statements = parse_sql(repaired_sql, options)
        except Exception:
            return sql

    if not statements:
        return sql

    formatted: list[str] = []
    for statement in statements:
        if statement is None:
            continue
        result = format_statement(statement, options)
        if result is None:
            return sql
        formatted.append(case_keywords(result.rstrip(), options.keyword_case))

    output = ";\n\n".join(formatted)
    if stripped_sql.rstrip().endswith(";"):
        output += ";"
    if line_comments:
        output = restore_line_comments(output, line_comments, options)
    if trailing_newline:
        output += "\n"
    return output


def parse_sql(sql: str, options: FormatOptions) -> list[exp.Expression | None]:
    sqlglot_logger = logging.getLogger("sqlglot")
    was_disabled = sqlglot_logger.disabled
    sqlglot_logger.disabled = True
    try:
        return sqlglot.parse(sql, read=options.dialect)
    finally:
        sqlglot_logger.disabled = was_disabled


def repair_missing_join_keywords(sql: str) -> str:
    # Older sql-neatfmt versions emitted "INNER table ON ...", "CROSS table",
    # and "LEFT OUTER table ON ..." by dropping JOIN. Repair those exact
    # malformed join keywords before falling back unchanged.
    out: list[str] = []
    i = 0
    quote: str | None = None

    while i < len(sql):
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if quote is not None:
            out.append(char)
            if char == "\\" and nxt:
                out.append(nxt)
                i += 2
                continue
            if char == quote:
                if nxt == quote:
                    out.append(nxt)
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        repair = missing_join_keyword_repair(sql, i)
        if repair is not None:
            text, i = repair
            out.append(text)
            continue

        if char in {"'", '"', "`"}:
            out.append(char)
            quote = char
            i += 1
            continue

        out.append(char)
        i += 1

    return "".join(out)


def missing_join_keyword_repair(sql: str, index: int) -> tuple[str, int] | None:
    for keyword in ("inner", "cross"):
        if not starts_word(sql, index, keyword):
            continue
        after_keyword = index + len(keyword)
        after_space = consume_whitespace(sql, after_keyword)
        if next_word(sql, after_space) == "join":
            return None
        return sql[index:after_space] + "JOIN ", after_space

    for side in ("left", "right", "full"):
        if not starts_word(sql, index, side):
            continue
        after_side = index + len(side)
        after_side_space = consume_whitespace(sql, after_side)
        if next_word(sql, after_side_space) != "outer":
            return None
        after_outer = after_side_space + len("outer")
        after_outer_space = consume_whitespace(sql, after_outer)
        if next_word(sql, after_outer_space) == "join":
            return None
        return sql[index:after_outer_space] + "JOIN ", after_outer_space

    return None


def starts_word(sql: str, index: int, word: str) -> bool:
    end = index + len(word)
    return sql[index:end].lower() == word and is_word_boundary(sql, index, end)


def consume_whitespace(sql: str, index: int) -> int:
    while index < len(sql) and sql[index].isspace():
        index += 1
    return index


def next_word(sql: str, index: int) -> str:
    end = index
    while end < len(sql) and (sql[end].isalnum() or sql[end] == "_"):
        end += 1
    return sql[index:end].lower()


def is_word_boundary(sql: str, start: int, end: int) -> bool:
    before = sql[start - 1] if start > 0 else ""
    after = sql[end] if end < len(sql) else ""
    return not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_")


def unsafe_input(sql: str, options: FormatOptions) -> bool:
    if TEMPLATE_RE.search(sql) or BLOCK_COMMENT_RE.search(sql):
        return True
    return options.dialect == "oracle" and bool(ORACLE_UNSUPPORTED_RE.search(sql))


def strip_line_comments(sql: str) -> tuple[str, list[LineComment]]:
    lines = sql.splitlines(keepends=True)
    clean_lines: list[str] = []
    comments: list[tuple[int, str, str, str | None]] = []
    quote: str | None = None

    for index, line in enumerate(lines):
        body, newline = split_newline(line)
        comment_index, quote = find_line_comment(body, quote)
        if comment_index is None:
            clean_lines.append(line)
            continue

        code = body[:comment_index].rstrip()
        comment = body[comment_index:].rstrip()
        leading = body[: len(body) - len(body.lstrip())]
        inline_anchor = code.strip() or None
        comments.append((index, comment, leading, inline_anchor))
        clean_lines.append((code if inline_anchor else "") + newline)

    line_comments: list[LineComment] = []
    for index, comment, leading, inline_anchor in comments:
        following_anchor = None
        if inline_anchor is None:
            following_anchor = next_clean_anchor(clean_lines, index + 1)
        line_comments.append(
            LineComment(
                text=comment,
                leading=leading,
                inline_anchor=inline_anchor,
                following_anchor=following_anchor,
            )
        )

    return "".join(clean_lines), line_comments


def split_newline(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    if line.endswith("\r"):
        return line[:-1], "\r"
    return line, ""


def find_line_comment(line: str, quote: str | None) -> tuple[int | None, str | None]:
    i = 0
    while i < len(line):
        char = line[i]
        nxt = line[i + 1] if i + 1 < len(line) else ""

        if quote is not None:
            if char == "\\" and nxt:
                i += 2
                continue
            if char == quote:
                if nxt == quote:
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if char in {"'", '"', "`"}:
            quote = char
            i += 1
            continue
        if char == "-" and nxt == "-":
            return i, quote
        i += 1

    return None, quote


def next_clean_anchor(lines: list[str], start: int) -> str | None:
    for line in lines[start:]:
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def restore_line_comments(
    formatted_sql: str, comments: list[LineComment], options: FormatOptions
) -> str:
    lines = formatted_sql.splitlines()
    for comment in comments:
        if comment.inline_anchor:
            index = find_formatted_anchor(lines, comment.inline_anchor)
            if index is None:
                lines.append(comment_line(comment, options))
            else:
                lines[index] = lines[index].rstrip() + " " + comment.text
            continue

        index = find_formatted_anchor(lines, comment.following_anchor)
        line = comment_line(comment, options)
        if index is None:
            lines.append(line)
        else:
            lines.insert(index, line)
    return "\n".join(lines)


def find_formatted_anchor(lines: list[str], anchor: str | None) -> int | None:
    if not anchor:
        return None

    for needle in comment_anchor_candidates(anchor):
        for index, line in enumerate(lines):
            haystack = canonical_comment_anchor(line)
            if needle in haystack:
                return index
    return None


def comment_anchor_candidates(anchor: str) -> list[str]:
    candidates = [canonical_comment_anchor(anchor)]
    statement_matchers = [
        r"^\s*insert\s+into\s+([\w.`\"]+)",
        r"^\s*create\s+(?:temporary\s+)?table\s+([\w.`\"]+)",
        r"^\s*alter\s+table\s+([\w.`\"]+)",
        r"^\s*drop\s+table\s+([\w.`\"]+)",
        r"^\s*update\s+([\w.`\"]+)",
        r"^\s*delete\s+from\s+([\w.`\"]+)",
    ]
    for pattern in statement_matchers:
        match = re.match(pattern, anchor, flags=re.IGNORECASE)
        if match:
            keyword = re.match(r"^\s*(\w+)", anchor, flags=re.IGNORECASE)
            if keyword:
                candidates.append(canonical_comment_anchor(f"{keyword.group(1)} {match.group(1)}"))

    canonical = candidates[0]
    for size in (120, 80, 60, 40):
        if len(canonical) > size:
            candidates.append(canonical[:size])

    unique: list[str] = []
    for candidate in candidates:
        if len(candidate) >= 6 and candidate not in unique:
            unique.append(candidate)
    return unique


def canonical_comment_anchor(sql: str) -> str:
    comment_index, _ = find_line_comment(sql, None)
    if comment_index is not None:
        sql = sql[:comment_index]
    sql = sql.casefold().replace("!=", "<>")
    return "".join(char for char in sql if not char.isspace())


def comment_line(comment: LineComment, options: FormatOptions) -> str:
    if re.match(r"--\s*(and|or)\b", comment.text, flags=re.IGNORECASE):
        return " " * options.condition_indent + comment.text
    return comment.leading + comment.text


def format_statement(statement: exp.Expression, options: FormatOptions) -> str | None:
    if isinstance(statement, exp.Select):
        return format_select(statement, options)
    if isinstance(statement, exp.Union):
        return format_union(statement, options)
    if isinstance(statement, exp.Update):
        return format_update(statement, options)
    if isinstance(statement, exp.Delete):
        return format_delete(statement, options)
    if isinstance(statement, exp.Insert):
        return format_insert(statement, options)
    if isinstance(statement, exp.Create):
        return format_create(statement, options)
    if isinstance(statement, exp.Alter):
        return format_alter(statement, options)
    if isinstance(statement, exp.Drop):
        return format_drop(statement, options)
    if isinstance(statement, exp.Merge):
        return format_merge(statement, options)
    if isinstance(statement, exp.Command):
        return format_command(statement, options)
    return None


def sql_expr(expression: exp.Expression | None, options: FormatOptions) -> str:
    if expression is None:
        return ""
    special = special_sql(expression, options)
    if special is not None:
        return special
    sql = expression.sql(dialect=options.dialect, pretty=False, normalize_functions="lower")
    return clean_generated_sql(case_keywords(sql, "lower"))


def special_sql(expression: exp.Expression, options: FormatOptions) -> str | None:
    if isinstance(expression, exp.Coalesce) and options.dialect in {"mysql", "mariadb"}:
        expressions = list(expression.expressions)
        if expression.this is not None and len(expressions) == 1:
            return f"ifnull({sql_expr(expression.this, options)}, {sql_expr(expressions[0], options)})"
    if isinstance(expression, exp.Not):
        inner = expression.this
        if isinstance(inner, exp.Is) and isinstance(inner.expression, exp.Null):
            return f"{sql_expr(inner.this, options)} is not null"
        not_like = format_not_like(inner, options)
        if not_like is not None:
            return not_like
    if isinstance(expression, exp.Is) and isinstance(expression.expression, exp.Null):
        return f"{sql_expr(expression.this, options)} is null"
    return None


def format_not_like(expression: exp.Expression, options: FormatOptions) -> str | None:
    escape: exp.Expression | None = None
    if isinstance(expression, exp.Escape):
        escape = expression.expression
        expression = expression.this
    if not isinstance(expression, exp.Like):
        return None

    sql = f"{sql_expr(expression.this, options)} not like {sql_expr(expression.expression, options)}"
    if escape is not None:
        sql += " escape " + sql_expr(escape, options)
    return sql


def clean_generated_sql(sql: str) -> str:
    sql = re.sub(r"\bexists\(", "exists (", sql)
    sql = re.sub(r"\b(un)?pivot\(", r"\1pivot (", sql, flags=re.IGNORECASE)
    return sql


def sql_expr_without(expression: exp.Expression, options: FormatOptions, *keys: str) -> str:
    copied = expression.copy()
    for key in keys:
        copied.set(key, None)
    return sql_expr(copied, options)


def format_projection(expression: exp.Expression, options: FormatOptions) -> str:
    if isinstance(expression, exp.Alias):
        scalar_subquery = format_scalar_subquery(expression.this, options)
        if scalar_subquery is not None:
            lines = scalar_subquery.splitlines()
            lines[-1] += f" as {sql_expr(expression.args['alias'], options)}"
            return "\n".join(lines)
        return (
            f"{sql_expr(expression.this, options)}"
            f"{projection_alias_separator(expression)}"
            f"{sql_expr(expression.args['alias'], options)}"
        )
    scalar_subquery = format_scalar_subquery(expression, options)
    if scalar_subquery is not None:
        return scalar_subquery
    return sql_expr(expression, options)


def format_scalar_subquery(expression: exp.Expression, options: FormatOptions) -> str | None:
    if not isinstance(expression, exp.Subquery) or not isinstance(expression.this, exp.Select):
        return None

    return format_parenthesized_select(expression.this, options)


def format_parenthesized_select(select: exp.Select, options: FormatOptions) -> str | None:
    if not select.expressions:
        return None

    first_prefix = "select distinct " if select.args.get("distinct") else "select "
    first, *rest = [format_projection(item, options) for item in select.expressions]
    if rest:
        first += ","
    lines = ["(" + first_prefix + first]
    lines.extend(" " + item + ("," if index < len(rest) - 1 else "") for index, item in enumerate(rest))

    from_expr = select.args.get("from") or select.args.get("from_")
    if from_expr:
        relation = from_expr.this if isinstance(from_expr, exp.From) else from_expr
        lines.append(" from " + sql_expr(relation, options))
        for join in select.args.get("joins") or []:
            lines.extend(" " + line for line in format_join(join, options, options.join_indent))

    where = select.args.get("where")
    if where:
        lines.extend(" " + line for line in format_predicate_clause("where", where.this, options))

    group = select.args.get("group")
    if group:
        group_sql = sql_expr(group, options)
        lines.append(" " + (group_sql if group_sql.startswith("group by ") else "group by " + group_sql))

    having = select.args.get("having")
    if having:
        lines.append(" having " + sql_expr(having.this, options))

    order = select.args.get("order")
    if order:
        order_sql = sql_expr(order, options)
        lines.append(" " + (order_sql if order_sql.startswith("order by ") else "order by " + order_sql))

    lines[-1] += ")"
    return "\n".join(lines)


def format_exists_subquery(expression: exp.Expression, options: FormatOptions) -> str | None:
    if not isinstance(expression, exp.Exists) or not isinstance(expression.this, exp.Select):
        return None

    subquery = format_parenthesized_select(expression.this, options)
    if subquery is None:
        return None

    lines = subquery.splitlines()
    return "\n".join(["exists " + lines[0], *(" " * len("exists ") + line for line in lines[1:])])


def format_relation(expression: exp.Expression, options: FormatOptions) -> str:
    if isinstance(expression, exp.Table):
        base = sql_expr_without(expression, options, "alias", "joins")
        return append_alias(base, expression, options)
    if isinstance(expression, exp.Subquery):
        base = sql_expr_without(expression, options, "alias")
        return append_alias(base, expression, options)
    return sql_expr(expression, options)


def append_alias(sql: str, expression: exp.Expression, options: FormatOptions) -> str:
    alias = expression.args.get("alias")
    if not alias:
        return sql
    return f"{sql} {sql_expr(alias.this, options)}"


def case_keywords(sql: str, keyword_case: KeywordCase) -> str:
    # SQLGlot's compact generator is already structurally safe. Lowercasing
    # or uppercasing outside quoted spans gives us editor-friendly casing
    # without touching string literals or quoted identifiers.
    def convert(word: str) -> str:
        return word.upper() if keyword_case == "upper" else word.lower()

    def should_convert(word: str, next_index: int) -> bool:
        lower = word.lower()
        if lower in SQL_KEYWORDS:
            return True
        if lower not in SQL_FUNCTIONS:
            return False
        while next_index < len(sql) and sql[next_index].isspace():
            next_index += 1
        return next_index < len(sql) and sql[next_index] == "("

    def convert_word(word: str, next_index: int) -> str:
        if not should_convert(word, next_index):
            return word
        return convert(word)

    out: list[str] = []
    i = 0
    quote: str | None = None

    while i < len(sql):
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if quote is not None:
            out.append(char)
            if char == "\\" and nxt:
                out.append(nxt)
                i += 2
                continue
            if char == quote:
                if nxt == quote:
                    out.append(nxt)
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if char in {"'", '"', "`"}:
            out.append(char)
            quote = char
            i += 1
            continue

        if char.isalpha() or char == "_":
            j = i + 1
            while j < len(sql) and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            word = sql[i:j]
            out.append(convert_word(word, j))
            i = j
            continue

        out.append(char)
        i += 1

    return "".join(out)


def format_select(select: exp.Select, options: FormatOptions) -> str:
    short = maybe_short_select(select, options)
    if short:
        return short

    lines: list[str] = []
    with_lines = format_with(select.args.get("with_"), options)
    if with_lines:
        lines.extend(with_lines)

    expressions = list(select.expressions)
    first_prefix = "select distinct " if select.args.get("distinct") else "select "
    if expressions:
        first, *rest = format_projection_list(expressions, options)
        if rest:
            first += ","
        lines.extend(format_projection_item(first, first_prefix))
        rest_prefix = " " * len(first_prefix)
        for index, item in enumerate(rest):
            if index < len(rest) - 1:
                item += ","
            lines.extend(format_projection_item(item, rest_prefix))
    else:
        lines.append("select")

    from_sql = format_from(select, options)
    if from_sql:
        lines.extend(from_sql)

    where = select.args.get("where")
    if where:
        lines.extend(format_predicate_clause("where", where.this, options))

    group = select.args.get("group")
    if group:
        group_sql = sql_expr(group, options)
        if group_sql.startswith("group by "):
            lines.append(group_sql)
        else:
            lines.append("group by " + group_sql)

    having = select.args.get("having")
    if having:
        lines.extend(format_predicate_clause("having", having.this, options))

    order = select.args.get("order")
    if order:
        order_sql = sql_expr(order, options)
        if order_sql.startswith("order by "):
            lines.append(order_sql)
        else:
            lines.append("order by " + order_sql)

    limit = select.args.get("limit")
    if limit:
        lines.append(sql_expr(limit, options))

    offset = select.args.get("offset")
    if offset:
        lines.append(sql_expr(offset, options))

    return "\n".join(lines)


def format_projection_item(item: str, prefix: str) -> list[str]:
    lines = item.splitlines()
    return [prefix + line for line in lines]


def format_projection_list(expressions: list[exp.Expression], options: FormatOptions) -> list[str]:
    alignable: dict[int, tuple[str, str]] = {}
    for index, expression in enumerate(expressions):
        item = split_projection_alias(expression, options)
        if item is not None:
            alignable[index] = item

    if len(alignable) < 2:
        return [format_projection(expression, options) for expression in expressions]

    max_expression_width = max(len(expression_sql) for expression_sql, _ in alignable.values())
    formatted: list[str] = []
    for index, expression in enumerate(expressions):
        item = alignable.get(index)
        if item is None:
            formatted.append(format_projection(expression, options))
            continue

        expression_sql, alias_sql = item
        formatted.append(expression_sql.ljust(max_expression_width) + " " + alias_sql)
    return formatted


def projection_alias_separator(expression: exp.Alias) -> str:
    if isinstance(expression.this, exp.Literal):
        return " as "
    return " "


def split_projection_alias(
    expression: exp.Expression, options: FormatOptions
) -> tuple[str, str] | None:
    if not isinstance(expression, exp.Alias):
        return None
    if format_scalar_subquery(expression.this, options) is not None:
        return None

    expression_sql = sql_expr(expression.this, options)
    if "\n" in expression_sql:
        return None
    alias_sql = projection_alias_separator(expression).strip()
    if alias_sql:
        alias_sql += " "
    alias_sql += sql_expr(expression.args["alias"], options)
    return expression_sql, alias_sql


def format_with(with_expr: exp.With | None, options: FormatOptions) -> list[str]:
    if not with_expr:
        return []

    ctes = list(with_expr.expressions)
    if not ctes:
        return []

    lines = ["with recursive" if with_expr.args.get("recursive") else "with"]
    for index, cte in enumerate(ctes):
        alias = sql_expr(cte.args["alias"].this, options)
        body_sql = format_query_expression(cte.this, options)
        suffix = "," if index < len(ctes) - 1 else ""
        lines.append(f"  {alias} as (")
        lines.append(indent(body_sql, 4))
        lines.append(f"  ){suffix}")
    return lines


def maybe_short_select(select: exp.Select, options: FormatOptions) -> str | None:
    if len(select.expressions) != 1:
        return None
    if select.args.get("joins") or select.args.get("group") or select.args.get("having") or select.args.get("order"):
        return None
    where = select.args.get("where")
    if where and contains_logical(where.this):
        return None

    from_expr = select.args.get("from") or select.args.get("from_")
    if not from_expr:
        return None
    relation = from_expr.this if isinstance(from_expr, exp.From) else from_expr
    from_sql = "from " + format_relation(relation, options)
    select_keyword = "select distinct " if select.args.get("distinct") else "select "
    query = select_keyword + format_projection(select.expressions[0], options) + " " + from_sql
    if where:
        query += " where " + sql_expr(where.this, options)
    if len(query) <= options.short_query_max_width:
        return query
    return None


def format_from(select: exp.Select, options: FormatOptions) -> list[str]:
    from_expr = select.args.get("from") or select.args.get("from_")
    if not from_expr:
        return []

    relation = from_expr.this if isinstance(from_expr, exp.From) else from_expr
    prefix = "from "
    relation_sql = format_relation(relation, options)
    from_sql = prefix + relation_sql
    lines = wrap_derived_relation_if_long(prefix, relation, from_sql, options) or [from_sql]
    for join in select.args.get("joins") or []:
        lines.extend(format_join(join, options, options.join_indent))
    return lines


def format_union(union: exp.Union, options: FormatOptions) -> str:
    lines = format_with(union.args.get("with_"), options)
    left = format_query_expression(union.this, options)
    right = format_query_expression(union.expression, options)
    operator = "union" if union.args.get("distinct", True) else "union all"
    lines.extend([left, operator, right])

    order = union.args.get("order")
    if order:
        order_sql = sql_expr(order, options)
        lines.append(order_sql if order_sql.startswith("order by ") else "order by " + order_sql)

    limit = union.args.get("limit")
    if limit:
        lines.append(sql_expr(limit, options))

    offset = union.args.get("offset")
    if offset:
        lines.append(sql_expr(offset, options))

    return "\n".join(lines)


def format_query_expression(expression: exp.Expression, options: FormatOptions) -> str:
    if isinstance(expression, exp.Select):
        return format_select(expression, options)
    if isinstance(expression, exp.Union):
        return format_union(expression, options)
    return sql_expr(expression, options)


def format_derived_subquery_relation(
    expression: exp.Expression, options: FormatOptions
) -> str | None:
    if not isinstance(expression, exp.Subquery):
        return None

    body_lines = format_derived_query_body(expression.this, options)
    if not body_lines:
        return None

    lines = ["(" + body_lines[0], *body_lines[1:]]
    pivots = expression.args.get("pivots") or []
    pivot_sql = "".join(" " + sql_expr(pivot, options) for pivot in pivots)
    alias = expression.args.get("alias")
    alias_sql = " " + sql_expr(alias.this, options) if alias else ""
    lines[-1] += ")" + pivot_sql + alias_sql
    return "\n".join(lines)


def format_derived_query_body(
    expression: exp.Expression, options: FormatOptions
) -> list[str] | None:
    if isinstance(expression, exp.Select):
        return format_inline_select(expression, options)
    if isinstance(expression, exp.Union):
        return format_union(expression, options).splitlines()
    return None


def wrap_derived_relation_if_long(
    prefix: str, relation: exp.Expression, compact_line: str, options: FormatOptions
) -> list[str] | None:
    multiline_relation = format_derived_subquery_relation(relation, options)
    if not multiline_relation or len(compact_line) <= options.short_query_max_width:
        return None
    return prefix_parenthesized_relation(prefix, multiline_relation)


def format_join(
    join: exp.Join,
    options: FormatOptions,
    indent_spaces: int = 0,
    condition_indent_spaces: int | None = None,
    continuation_indent_spaces: int | None = None,
    inline_single_condition: bool = True,
) -> list[str]:
    prefix = " " * indent_spaces
    side = (join.args.get("side") or "").lower()
    kind = (join.args.get("kind") or "join").lower()
    join_keyword = format_join_keyword(side, kind)
    join_prefix = f"{prefix}{join_keyword} "
    compact_relation = format_relation(join.this, options)
    join_sql = join_prefix + compact_relation
    on = join.args.get("on")
    if not on:
        return [join_sql]

    parts = split_logical(on)
    if len(parts) == 1 and inline_single_condition:
        inline_join_sql = join_sql + " on " + sql_expr(parts[0], options)
        lines = wrap_derived_relation_if_long(join_prefix, join.this, inline_join_sql, options)
        if lines:
            lines[-1] += " on " + sql_expr(parts[0], options)
            return lines
        return [join_sql + " on " + sql_expr(parts[0], options)]

    lines = wrap_derived_relation_if_long(join_prefix, join.this, join_sql, options) or [join_sql]
    condition_indent = (
        condition_indent_spaces
        if condition_indent_spaces is not None
        else indent_spaces + options.join_condition_indent
    )
    continuation_indent = (
        continuation_indent_spaces
        if continuation_indent_spaces is not None
        else condition_indent - 1
    )
    lines.append(" " * condition_indent + "on " + sql_expr(parts[0], options))
    lines.extend(
        " " * continuation_indent + op + " " + sql_expr(part, options)
        for op, part in parts[1:]
    )
    return lines


def format_join_keyword(side: str, kind: str) -> str:
    if kind in {"inner", "cross"} and not side:
        return f"{kind} join"
    if side and kind == "join":
        return f"{side} join"
    if side and kind:
        return f"{side} {kind} join"
    return kind


def format_predicate_clause(
    keyword: str, predicate: exp.Expression, options: FormatOptions
) -> list[str]:
    parts = split_logical(predicate)
    if len(parts) == 1:
        prefix = f"{keyword} "
        return prefix_multiline(
            prefix,
            format_condition_expression(parts[0], options, len(prefix)),
        )

    prefix = f"{keyword} "
    lines = prefix_multiline(
        prefix,
        format_condition_expression(parts[0], options, len(prefix)),
    )
    for op, part in parts[1:]:
        prefix = " " * options.condition_indent + op + " "
        lines.extend(
            prefix_multiline(prefix, format_condition_expression(part, options, len(prefix)))
        )
    return lines


def format_condition_expression(
    expression: exp.Expression, options: FormatOptions, prefix_width: int
) -> str:
    compact = sql_expr(expression, options)
    multiline = format_exists_subquery(expression, options)
    if multiline is not None and prefix_width + len(compact) > options.short_query_max_width:
        return multiline
    return compact


def prefix_multiline(prefix: str, text: str) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return [prefix.rstrip()]
    return [prefix + lines[0], *(" " * len(prefix) + line for line in lines[1:])]


def prefix_parenthesized_relation(prefix: str, text: str) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return [prefix.rstrip()]
    continuation = " " * (len(prefix) + 1)
    return [prefix + lines[0], *(continuation + line for line in lines[1:])]


LogicalPart = exp.Expression | tuple[str, exp.Expression]


def split_logical(expression: exp.Expression) -> list[LogicalPart]:
    if isinstance(expression, exp.And):
        return [
            *split_logical(expression.left),
            *prefix_logical("and", split_logical(expression.right)),
        ]
    if isinstance(expression, exp.Or):
        return [
            *split_logical(expression.left),
            *prefix_logical("or", split_logical(expression.right)),
        ]
    return [expression]


def prefix_logical(operator: str, parts: list[LogicalPart]) -> list[tuple[str, exp.Expression]]:
    prefixed: list[tuple[str, exp.Expression]] = []
    for part in parts:
        if isinstance(part, tuple):
            prefixed.append(part)
        else:
            prefixed.append((operator, part))
    return prefixed


def contains_logical(expression: exp.Expression) -> bool:
    return any(isinstance(node, (exp.And, exp.Or)) for node in expression.walk())


def format_update(update: exp.Update, options: FormatOptions) -> str:
    table = update.this
    lines = ["update " + format_relation(table, options)]

    if isinstance(table, exp.Table):
        for join in table.args.get("joins") or []:
            lines.extend(
                format_join(
                    join,
                    options,
                    options.update_join_indent,
                    options.update_join_condition_indent,
                    options.update_join_continuation_indent,
                    inline_single_condition=False,
                )
            )

    if update.expressions:
        lines.extend(format_aligned_set(update.expressions, options))

    from_expr = update.args.get("from") or update.args.get("from_")
    if from_expr:
        relation = from_expr.this if isinstance(from_expr, exp.From) else from_expr
        lines.append("from " + format_relation(relation, options))

    where = update.args.get("where")
    if where:
        lines.extend(format_predicate_clause("where", where.this, options))

    returning = format_returning(update.args.get("returning"), options)
    if returning:
        lines.extend(returning)

    return "\n".join(lines)


def format_delete(delete: exp.Delete, options: FormatOptions) -> str:
    delete_targets = delete.args.get("tables") or []
    if delete_targets:
        lines = ["delete " + ", ".join(sql_expr(target, options) for target in delete_targets)]
        lines.append("from " + format_relation(delete.this, options))
        if isinstance(delete.this, exp.Table):
            for join in delete.this.args.get("joins") or []:
                lines.extend(format_join(join, options, options.join_indent))
    else:
        lines = ["delete from " + format_relation(delete.this, options)]

    using = delete.args.get("using")
    if using:
        expressions = using if isinstance(using, list) else [using]
        first, *rest = [format_relation(expression, options) for expression in expressions]
        lines.append("using " + first + ("," if rest else ""))
        lines.extend(
            " " * len("using ") + item + ("," if index < len(rest) - 1 else "")
            for index, item in enumerate(rest)
        )

    where = delete.args.get("where")
    if where:
        lines.extend(format_predicate_clause("where", where.this, options))
    returning = format_returning(delete.args.get("returning"), options)
    if returning:
        lines.extend(returning)

    order = delete.args.get("order")
    if order:
        order_sql = sql_expr(order, options)
        lines.append(order_sql if order_sql.startswith("order by ") else "order by " + order_sql)

    limit = delete.args.get("limit")
    if limit:
        lines.append(sql_expr(limit, options))

    return "\n".join(lines)


def format_merge(merge: exp.Merge, options: FormatOptions) -> str:
    lines = ["merge into " + format_relation(merge.this, options)]

    using = merge.args.get("using")
    if using:
        lines.extend(format_merge_using(using, options))

    on = merge.args.get("on")
    if on:
        lines.append("on " + sql_expr(on, options))

    whens = merge.args.get("whens")
    if whens:
        for when in whens.expressions:
            lines.extend(format_merge_when(when, options))

    returning = format_returning(merge.args.get("returning"), options)
    if returning:
        lines.extend(returning)

    return "\n".join(lines)


def format_merge_using(using: exp.Expression, options: FormatOptions) -> list[str]:
    if isinstance(using, exp.Subquery) and isinstance(using.this, exp.Select):
        body_lines = format_inline_select(using.this, options)
        lines = ["using (" + body_lines[0]]
        lines.extend(" " * len("using (") + line for line in body_lines[1:])

        alias = using.args.get("alias")
        if alias:
            lines[-1] += ") " + sql_expr(alias.this, options)
        else:
            lines[-1] += ")"
        return lines

    return ["using " + format_relation(using, options)]


def format_inline_select(select: exp.Select, options: FormatOptions) -> list[str]:
    lines: list[str] = []
    expressions = list(select.expressions)
    first_prefix = "select distinct " if select.args.get("distinct") else "select "
    if expressions:
        projections = [sql_expr(expression, options) for expression in expressions]
        compact_select = first_prefix + ", ".join(projections)
        if len(compact_select) <= options.short_query_max_width:
            lines.append(compact_select)
        else:
            first, *rest = projections
            if rest:
                first += ","
            lines.append(first_prefix + first)
            rest_prefix = " " * len(first_prefix)
            lines.extend(
                rest_prefix + item + ("," if index < len(rest) - 1 else "")
                for index, item in enumerate(rest)
            )
    else:
        lines.append("select")

    from_sql = format_from(select, options)
    if from_sql:
        lines.extend(from_sql)

    where = select.args.get("where")
    if where:
        lines.extend(format_predicate_clause("where", where.this, options))

    group = select.args.get("group")
    if group:
        group_sql = sql_expr(group, options)
        lines.append(group_sql if group_sql.startswith("group by ") else "group by " + group_sql)

    having = select.args.get("having")
    if having:
        lines.extend(format_predicate_clause("having", having.this, options))

    order = select.args.get("order")
    if order:
        order_sql = sql_expr(order, options)
        lines.append(order_sql if order_sql.startswith("order by ") else "order by " + order_sql)

    return lines


def format_merge_when(when: exp.When, options: FormatOptions) -> list[str]:
    matched = "matched" if when.args.get("matched") else "not matched"
    condition = when.args.get("condition")
    line = "when " + matched
    if condition:
        line += " and " + sql_expr(condition, options)
    line += " then"

    then = when.args.get("then")
    if isinstance(then, exp.Update):
        return [line, *indent_lines(format_merge_update(then, options), 4)]
    if isinstance(then, exp.Insert):
        return [line, *indent_lines(format_merge_insert(then, options), 4)]
    if then:
        return [line + " " + sql_expr(then, options)]
    return [line]


def format_merge_update(update: exp.Update, options: FormatOptions) -> list[str]:
    lines = ["update"]
    if update.expressions:
        lines.extend(format_aligned_set(update.expressions, options))

    where = update.args.get("where")
    if where:
        lines.extend(format_predicate_clause("where", where.this, options))
    return lines


def format_aligned_set(assignments: list[exp.Expression], options: FormatOptions) -> list[str]:
    return format_aligned_assignments(assignments, options, "set ")


def format_aligned_assignments(
    assignments: list[exp.Expression], options: FormatOptions, first_prefix: str
) -> list[str]:
    if not assignments:
        return []
    if not all(isinstance(assignment, exp.EQ) for assignment in assignments):
        first, *rest = [sql_expr(assignment, options) for assignment in assignments]
        lines = [first_prefix + first + ("," if rest else "")]
        lines.extend(
            " " * len(first_prefix) + item + ("," if index < len(rest) - 1 else "")
            for index, item in enumerate(rest)
        )
        return lines

    pairs = [(sql_expr(assignment.this, options), assignment.expression) for assignment in assignments]
    max_left = max(len(left) for left, _ in pairs)
    lines: list[str] = []
    rest_prefix = " " * len(first_prefix)
    for index, (left, right_expression) in enumerate(pairs):
        suffix = "," if index < len(pairs) - 1 else ""
        prefix = first_prefix if index == 0 else rest_prefix
        line_prefix = prefix + left.ljust(max_left) + " = "
        right = format_assignment_expression(right_expression, options, len(line_prefix) + len(suffix))
        lines.extend(suffix_multiline(prefix_multiline(line_prefix, right), suffix))
    return lines


def format_assignment_expression(
    expression: exp.Expression, options: FormatOptions, prefix_width: int
) -> str:
    compact = sql_expr(expression, options)
    multiline = format_scalar_subquery(expression, options)
    if multiline is not None and prefix_width + len(compact) > options.short_query_max_width:
        return multiline
    return compact


def suffix_multiline(lines: list[str], suffix: str) -> list[str]:
    if suffix and lines:
        lines[-1] += suffix
    return lines


def format_merge_insert(insert: exp.Insert, options: FormatOptions) -> list[str]:
    lines = ["insert " + sql_expr(insert.this, options)]
    expression = insert.args.get("expression")
    if expression:
        lines.append("values " + sql_expr(expression, options))

    where = insert.args.get("where")
    if where:
        lines.extend(format_predicate_clause("where", where.this, options))
    return lines


def indent_lines(lines: list[str], spaces: int) -> list[str]:
    prefix = " " * spaces
    return [prefix + line if line else line for line in lines]


def format_insert(insert: exp.Insert, options: FormatOptions) -> str:
    target = sql_expr(insert.this, options)
    source = insert.args.get("expression")
    if isinstance(source, exp.Select):
        lines = ["insert into " + target]
        lines.append(format_select(source, options))
        returning = format_returning(insert.args.get("returning"), options)
        if returning:
            lines.extend(returning)
        return "\n".join(lines)

    if isinstance(source, exp.Values):
        formatted = format_values_insert(insert, source, options)
        if formatted is not None:
            return formatted

    sql = sql_expr(insert, options)
    return format_sqlglot_lines(sql, options)


def format_values_insert(insert: exp.Insert, values: exp.Values, options: FormatOptions) -> str | None:
    sql = sql_expr(insert, options)
    if len(sql) <= options.short_query_max_width:
        return sql

    tuples = list(values.expressions)
    if not tuples:
        return sql

    lines = ["insert into " + format_insert_target(insert.this, options)]
    lines.extend(format_values_lines(tuples, options))

    conflict = insert.args.get("conflict")
    if conflict:
        lines.extend(format_on_conflict(conflict, options))

    returning = format_returning(insert.args.get("returning"), options)
    if returning:
        lines.extend(returning)

    return "\n".join(lines)


def format_insert_target(target: exp.Expression, options: FormatOptions) -> str:
    if isinstance(target, exp.Schema):
        table = sql_expr(target.this, options)
        columns = [sql_expr(column, options) for column in target.expressions]
        return f"{table} ({', '.join(columns)})"

    return sql_expr(target, options)


def format_values_lines(tuples: list[exp.Expression], options: FormatOptions) -> list[str]:
    if len(tuples) == 1:
        return ["values " + format_tuple_values(tuples[0], options)]

    lines: list[str] = []
    values_prefix = "values "
    for index, tuple_expr in enumerate(tuples):
        suffix = "," if index < len(tuples) - 1 else ""
        prefix = values_prefix if index == 0 else " " * len(values_prefix)
        lines.append(prefix + format_tuple_values(tuple_expr, options) + suffix)
    return lines


def format_tuple_values(tuple_expr: exp.Expression, options: FormatOptions) -> str:
    if isinstance(tuple_expr, exp.Tuple):
        return "(" + ", ".join(sql_expr(item, options) for item in tuple_expr.expressions) + ")"
    return sql_expr(tuple_expr, options)


def format_on_conflict(conflict: exp.OnConflict, options: FormatOptions) -> list[str]:
    expressions = list(conflict.expressions)
    action = sql_expr(conflict.args.get("action"), options).lower()
    if action != "do update" or len(expressions) <= 1:
        return [sql_expr(conflict, options)]

    target = format_conflict_target(conflict, options)
    prefix = "on conflict" + target + " do update set "
    lines = format_aligned_assignments(expressions, options, prefix)

    where = conflict.args.get("where")
    if where:
        lines.extend(format_predicate_clause("where", where.this, options))
    return lines


def format_conflict_target(conflict: exp.OnConflict, options: FormatOptions) -> str:
    constraint = conflict.args.get("constraint")
    if constraint:
        return " on constraint " + sql_expr(constraint, options)

    keys = conflict.args.get("conflict_keys") or []
    if keys:
        return "(" + ", ".join(sql_expr(key, options) for key in keys) + ")"
    return ""


def format_create(create: exp.Create, options: FormatOptions) -> str:
    formatted_table = format_create_table(create, options)
    if formatted_table:
        return formatted_table

    sql = sql_expr(create, options)
    formatted = format_create_table_sql(sql, options)
    if formatted:
        return formatted
    return sql


def format_drop(drop: exp.Drop, options: FormatOptions) -> str:
    return sql_expr(drop, options)


def format_create_table(create: exp.Create, options: FormatOptions) -> str | None:
    if str(create.args.get("kind") or "").lower() != "table":
        return None

    schema = create.this
    if not isinstance(schema, exp.Schema):
        return None

    definitions = list(schema.expressions)
    if len(definitions) <= 1:
        return None

    sql = sql_expr(create, options)
    if len(sql) <= options.short_query_max_width:
        return None

    start = sql.find("(")
    if start == -1:
        return None

    head = sql[:start].rstrip()
    lines = [head, "("]
    lines.extend(format_create_table_definitions(definitions, options))

    properties = format_create_table_properties(create.args.get("properties"), options)
    if properties:
        lines.append(") " + properties[0])
        lines.extend("  " + property_sql for property_sql in properties[1:])
    else:
        lines.append(")")
    return "\n".join(lines)


def format_create_table_definitions(
    definitions: list[exp.Expression], options: FormatOptions
) -> list[str]:
    column_layouts = [
        split_column_definition(definition, options)
        for definition in definitions
        if isinstance(definition, exp.ColumnDef)
    ]
    name_width = max((len(column.name) for column in column_layouts), default=0) + 1

    not_null_kind_widths = [
        len(column.kind) for column in column_layouts if column.has_not_null and column.kind
    ]
    if not_null_kind_widths:
        not_null_start = max(not_null_kind_widths) + 1
        constraint_start = not_null_start + len("not null") + 1
    else:
        constraint_start = max((len(column.kind) for column in column_layouts), default=0) + 1
        not_null_start = constraint_start

    lines: list[str] = []
    for index, definition in enumerate(definitions):
        suffix = "," if index < len(definitions) - 1 else ""
        if isinstance(definition, exp.ColumnDef):
            column = split_column_definition(definition, options)
            line = format_create_table_column(
                column,
                name_width,
                not_null_start,
                constraint_start,
            )
        else:
            line = " " * 4 + format_table_constraint(definition, options)
        lines.append(line + suffix)
    return lines


def split_column_definition(
    column: exp.ColumnDef, options: FormatOptions
) -> ColumnDefinitionLayout:
    constraints: list[str] = []
    has_not_null = False
    for constraint in column.args.get("constraints") or []:
        kind = constraint.args.get("kind")
        if isinstance(kind, exp.NotNullColumnConstraint):
            has_not_null = True
            continue
        constraints.append(format_column_constraint(constraint, options))

    kind = column.args.get("kind")
    return ColumnDefinitionLayout(
        name=sql_expr(column.this, options),
        kind=sql_expr(kind, options) if kind else "",
        constraints=constraints,
        has_not_null=has_not_null,
    )


def format_column_constraint(constraint: exp.ColumnConstraint, options: FormatOptions) -> str:
    sql = sql_expr(constraint, options)
    if isinstance(constraint.args.get("kind"), exp.DefaultColumnConstraint):
        return re.sub(r"\bcurrent_timestamp\(\)", "current_timestamp", sql, flags=re.IGNORECASE)
    return sql


def format_create_table_column(
    column: ColumnDefinitionLayout,
    name_width: int,
    not_null_start: int,
    constraint_start: int,
) -> str:
    line = " " * 4 + pad_to(column.name, name_width)
    constraints = " ".join(column.constraints)
    if column.has_not_null:
        line += pad_to(column.kind, not_null_start) + "not null"
        if constraints:
            line += " " + constraints
        return line

    if constraints:
        start = not_null_start if starts_at_not_null_slot(constraints) else constraint_start
        line += pad_to(column.kind, start) + constraints
        return line

    return line + column.kind


def starts_at_not_null_slot(constraints: str) -> bool:
    return bool(re.match(r"(primary\s+key|unique)\b", constraints, flags=re.IGNORECASE))


def pad_to(text: str, width: int) -> str:
    return text + " " * max(width - len(text), 1)


def format_table_constraint(definition: exp.Expression, options: FormatOptions) -> str:
    if options.dialect in {"mysql", "mariadb"}:
        mysql_constraint = format_mysql_table_constraint(definition, options)
        if mysql_constraint is not None:
            return mysql_constraint
    return sql_expr(definition, options)


def format_mysql_table_constraint(
    definition: exp.Expression, options: FormatOptions
) -> str | None:
    if isinstance(definition, exp.UniqueColumnConstraint):
        schema = definition.this
        if not isinstance(schema, exp.Schema):
            return None
        name = sql_expr(schema.this, options)
        columns = ", ".join(sql_expr(expression, options) for expression in schema.expressions)
        suffix = format_index_constraint_options(definition, options)
        return f"unique key {name} ({columns}){suffix}"

    if isinstance(definition, exp.IndexColumnConstraint):
        name = sql_expr(definition.this, options)
        columns = ", ".join(
            format_index_constraint_expression(expression, options)
            for expression in definition.expressions
        )
        suffix = format_index_constraint_options(definition, options)
        index_kind = sql_expr(definition.args.get("kind"), options)
        prefix = f"{index_kind} key" if index_kind else "key"
        return f"{prefix} {name} ({columns}){suffix}"

    return None


def format_index_constraint_expression(
    expression: exp.Expression, options: FormatOptions
) -> str:
    if isinstance(expression, exp.Ordered):
        return sql_expr(expression.this, options)
    return sql_expr(expression, options)


def format_index_constraint_options(
    definition: exp.Expression, options: FormatOptions
) -> str:
    options_sql = [
        sql_expr(option, options)
        for option in definition.args.get("options") or []
        if sql_expr(option, options)
    ]
    if not options_sql:
        return ""
    return " " + " ".join(options_sql)


def format_create_table_properties(
    properties: exp.Properties | None, options: FormatOptions
) -> list[str]:
    if not isinstance(properties, exp.Properties):
        return []

    lines: list[str] = []
    for property_expr in properties.expressions:
        property_sql = format_create_table_property(property_expr, options)
        if not property_sql:
            continue
        if lines and should_join_table_property(lines[-1], property_sql):
            lines[-1] += " " + property_sql
        else:
            lines.append(property_sql)
    return lines


def should_join_table_property(previous: str, current: str) -> bool:
    return (
        current.startswith("comment ")
        and ("charset" in previous or "character set" in previous)
    )


def format_create_table_property(
    property_expr: exp.Expression, options: FormatOptions
) -> str:
    value = property_expr.this
    if isinstance(property_expr, exp.EngineProperty) and value is not None:
        return "engine = " + sql_expr(value, options)
    if isinstance(property_expr, exp.AutoIncrementProperty) and value is not None:
        return "auto_increment = " + sql_expr(value, options)
    if isinstance(property_expr, exp.CharacterSetProperty) and value is not None:
        prefix = "default charset" if property_expr.args.get("default") else "charset"
        return prefix + " = " + sql_expr(value, options)
    if isinstance(property_expr, exp.SchemaCommentProperty) and value is not None:
        return "comment = " + sql_expr(value, options)

    sql = sql_expr(property_expr, options)
    sql = re.sub(r"\bdefault\s+character\s+set\b", "default charset", sql, flags=re.IGNORECASE)
    return re.sub(r"\s*=\s*", " = ", sql)


def format_create_table_sql(sql: str, options: FormatOptions) -> str | None:
    if len(sql) <= options.short_query_max_width:
        return None
    match = re.match(
        r"^create\s+(?:temporary\s+)?table\b",
        sql,
        flags=re.IGNORECASE,
    )
    if not match:
        return None

    start = sql.find("(", match.end())
    if start == -1:
        return None

    end = find_matching_parenthesis(sql, start)
    if end is None:
        return None

    head = sql[:start].rstrip()
    body = sql[start + 1 : end]
    tail = sql[end + 1 :].strip()
    definitions = [item.strip() for item in split_top_level(body, ",") if item.strip()]
    if len(definitions) <= 1:
        return None

    lines = [head, "("]
    for index, definition in enumerate(definitions):
        suffix = "," if index < len(definitions) - 1 else ""
        lines.append(" " * 4 + definition + suffix)

    close = ")"
    if tail:
        close += " " + tail
    lines.append(close)
    return "\n".join(lines)


def format_alter(alter: exp.Alter, options: FormatOptions) -> str:
    sql = sql_expr(alter, options)
    formatted = format_alter_table_sql(sql, options)
    if formatted:
        return formatted

    lines = [line.strip() for line in sql.splitlines() if line.strip()]
    if len(lines) <= 1:
        return sql
    return "\n".join([lines[0], *(indent(line, options.alter_action_indent) for line in lines[1:])])


def format_command(command: exp.Command, options: FormatOptions) -> str | None:
    if str(command.this).lower() != "alter":
        return None

    sql = sql_expr(command, options)
    formatted = format_alter_table_sql(sql, options)
    if formatted:
        return formatted
    return sql


def format_alter_table_sql(sql: str, options: FormatOptions) -> str | None:
    match = re.match(r"^(alter\s+table\s+\S+)\s+(.+)$", sql, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None

    head, actions_sql = match.groups()
    actions = split_top_level(actions_sql, ",")
    if len(actions) <= 1:
        return None

    lines = [head]
    for index, action in enumerate(actions):
        suffix = "," if index < len(actions) - 1 else ""
        lines.append(" " * options.alter_action_indent + action.strip() + suffix)
    return "\n".join(lines)


def format_returning(returning: exp.Returning | None, options: FormatOptions) -> list[str]:
    if not returning:
        return []

    expressions = [sql_expr(expression, options) for expression in returning.expressions]
    if not expressions:
        return []
    if len(expressions) == 1:
        return ["returning " + expressions[0]]

    compact = "returning " + ", ".join(expressions)
    if len(expressions) <= 2 and len(compact) <= options.short_query_max_width:
        return [compact]

    first, *rest = expressions
    lines = ["returning " + first + ","]
    lines.extend(
        " " * 4 + item + ("," if index < len(rest) - 1 else "")
        for index, item in enumerate(rest)
    )
    return lines


def split_top_level(sql: str, separator: str) -> list[str]:
    parts: list[str] = []
    start = 0
    depth = 0
    quote: str | None = None
    i = 0

    while i < len(sql):
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if quote is not None:
            if char == "\\" and nxt:
                i += 2
                continue
            if char == quote:
                if nxt == quote:
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if char in {"'", '"', "`"}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        elif char == separator and depth == 0:
            parts.append(sql[start:i])
            start = i + 1
        i += 1

    parts.append(sql[start:])
    return parts


def find_matching_parenthesis(sql: str, start: int) -> int | None:
    depth = 0
    quote: str | None = None
    i = start

    while i < len(sql):
        char = sql[i]
        nxt = sql[i + 1] if i + 1 < len(sql) else ""

        if quote is not None:
            if char == "\\" and nxt:
                i += 2
                continue
            if char == quote:
                if nxt == quote:
                    i += 2
                    continue
                quote = None
            i += 1
            continue

        if char in {"'", '"', "`"}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1

    return None


def format_sqlglot_lines(sql: str, options: FormatOptions) -> str:
    # Bridge for non-SELECT statements. It keeps SQLGlot's clause boundaries,
    # then applies the same compact where/join condition rules where obvious.
    lines = [line.rstrip() for line in sql.splitlines()]
    if len(lines) == 1:
        return sql
    return "\n".join(lines)


def indent(sql: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line else line for line in sql.splitlines())
