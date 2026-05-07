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
        sqlglot_logger = logging.getLogger("sqlglot")
        was_disabled = sqlglot_logger.disabled
        sqlglot_logger.disabled = True
        try:
            statements = sqlglot.parse(stripped_sql, read=options.dialect)
        finally:
            sqlglot_logger.disabled = was_disabled
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

    needle = canonical_comment_anchor(anchor)
    for index, line in enumerate(lines):
        haystack = canonical_comment_anchor(line)
        if needle and needle in haystack:
            return index
    return None


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
    if isinstance(expression, exp.Is) and isinstance(expression.expression, exp.Null):
        return f"{sql_expr(expression.this, options)} is null"
    return None


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
        return f"{sql_expr(expression.this, options)} {sql_expr(expression.args['alias'], options)}"
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
    return expression_sql, sql_expr(expression.args["alias"], options)


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
    if not isinstance(expression, exp.Subquery) or not isinstance(expression.this, exp.Select):
        return None

    body_lines = format_inline_select(expression.this, options)
    if not body_lines:
        return None

    lines = ["(" + body_lines[0], *body_lines[1:]]
    pivots = expression.args.get("pivots") or []
    pivot_sql = "".join(" " + sql_expr(pivot, options) for pivot in pivots)
    alias = expression.args.get("alias")
    alias_sql = " " + sql_expr(alias.this, options) if alias else ""
    lines[-1] += ")" + pivot_sql + alias_sql
    return "\n".join(lines)


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
    join_keyword = " ".join(part for part in (side, kind) if part)
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
    sql = sql_expr(create, options)
    formatted = format_create_table_sql(sql, options)
    if formatted:
        return formatted
    return sql


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

    lines = [head + " ("]
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
