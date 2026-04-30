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


TEMPLATE_RE = re.compile(
    r"</?(select|insert|update|delete|include|if|where|foreach|choose|when|otherwise|trim|set)\b|[#][$]?\{",
    re.IGNORECASE,
)
COMMENT_RE = re.compile(r"(--|/\*)")
SQL_KEYWORDS = {
    "add",
    "all",
    "alter",
    "and",
    "as",
    "asc",
    "between",
    "bigint",
    "boolean",
    "by",
    "case",
    "cast",
    "char",
    "column",
    "create",
    "cross",
    "current_timestamp",
    "date",
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
    "first",
    "from",
    "full",
    "group",
    "having",
    "in",
    "index",
    "inner",
    "insert",
    "int",
    "integer",
    "into",
    "is",
    "join",
    "key",
    "left",
    "limit",
    "matched",
    "merge",
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
    "primary",
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
    "true",
    "union",
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
    "coalesce",
    "concat",
    "count",
    "date_format",
    "decode",
    "ifnull",
    "lag",
    "lead",
    "length",
    "lower",
    "max",
    "min",
    "now",
    "nvl",
    "rank",
    "row_number",
    "round",
    "substr",
    "substring",
    "sum",
    "to_char",
    "to_date",
    "upper",
    "values",
}


def format_sql(sql: str, options: FormatOptions | None = None) -> str:
    options = options or FormatOptions()
    if unsafe_input(sql):
        return sql

    trailing_newline = sql.endswith("\n")
    try:
        sqlglot_logger = logging.getLogger("sqlglot")
        was_disabled = sqlglot_logger.disabled
        sqlglot_logger.disabled = True
        try:
            statements = sqlglot.parse(sql, read=options.dialect)
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

    output = ";\n".join(formatted)
    if sql.rstrip().endswith(";"):
        output += ";"
    if trailing_newline:
        output += "\n"
    return output


def unsafe_input(sql: str) -> bool:
    return bool(TEMPLATE_RE.search(sql) or COMMENT_RE.search(sql))


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
        return sql_expr(statement, options)
    if isinstance(statement, exp.Alter):
        return format_alter(statement, options)
    if isinstance(statement, exp.Merge):
        return sql_expr(statement, options)
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

    select = expression.this
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
        lines.append(" where " + sql_expr(where.this, options))

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
        first, *rest = [format_projection(expression, options) for expression in expressions]
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


def format_with(with_expr: exp.With | None, options: FormatOptions) -> list[str]:
    if not with_expr:
        return []

    ctes = list(with_expr.expressions)
    if not ctes:
        return []

    lines = ["with"]
    for index, cte in enumerate(ctes):
        alias = sql_expr(cte.args["alias"].this, options)
        body = cte.this
        if isinstance(body, exp.Select):
            body_sql = format_select(body, options)
        else:
            body_sql = sql_expr(body, options)
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
    lines = ["from " + format_relation(relation, options)]
    for join in select.args.get("joins") or []:
        lines.extend(format_join(join, options, options.join_indent))
    return lines


def format_union(union: exp.Union, options: FormatOptions) -> str:
    left = format_query_expression(union.this, options)
    right = format_query_expression(union.expression, options)
    operator = "union" if union.args.get("distinct", True) else "union all"
    lines = [left, operator, right]

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
    join_sql = f"{prefix}{join_keyword} {format_relation(join.this, options)}"
    on = join.args.get("on")
    if not on:
        return [join_sql]

    parts = split_logical(on)
    if len(parts) == 1 and inline_single_condition:
        return [join_sql + " on " + sql_expr(parts[0], options)]

    lines = [join_sql]
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
    if contains_query(predicate):
        return [f"{keyword} {sql_expr(predicate, options)}"]

    parts = split_logical(predicate)
    if len(parts) == 1:
        return [f"{keyword} {sql_expr(parts[0], options)}"]

    lines = [f"{keyword} {sql_expr(parts[0], options)}"]
    lines.extend(
        " " * options.condition_indent + op + " " + sql_expr(part, options)
        for op, part in parts[1:]
    )
    return lines


LogicalPart = exp.Expression | tuple[str, exp.Expression]


def split_logical(expression: exp.Expression) -> list[LogicalPart]:
    if isinstance(expression, exp.And):
        return [*split_logical(expression.left), *prefix_logical("and", split_logical(expression.right))]
    if isinstance(expression, exp.Or):
        return [*split_logical(expression.left), *prefix_logical("or", split_logical(expression.right))]
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


def contains_query(expression: exp.Expression) -> bool:
    return any(isinstance(node, (exp.Select, exp.Subquery, exp.Exists)) for node in expression.walk())


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

    assignments = [sql_expr(assignment, options) for assignment in update.expressions]
    if assignments:
        first, *rest = assignments
        lines.append("set " + first + ("," if rest else ""))
        lines.extend(
            " " * len("set ") + assignment + ("," if index < len(rest) - 1 else "")
            for index, assignment in enumerate(rest)
        )

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

    lines = format_insert_target_lines(insert.this, options)
    lines.extend(format_values_lines(tuples, options, force_multiline=len(lines) > 1))

    conflict = insert.args.get("conflict")
    if conflict:
        lines.append(sql_expr(conflict, options))

    returning = format_returning(insert.args.get("returning"), options)
    if returning:
        lines.extend(returning)

    return "\n".join(lines)


def format_insert_target_lines(target: exp.Expression, options: FormatOptions) -> list[str]:
    if isinstance(target, exp.Schema):
        table = sql_expr(target.this, options)
        columns = [sql_expr(column, options) for column in target.expressions]
        compact = f"{table} ({', '.join(columns)})"
        if len("insert into " + compact) <= options.short_query_max_width:
            return ["insert into " + compact]

        lines = ["insert into " + table + " ("]
        lines.extend(
            "    " + column + ("," if index < len(columns) - 1 else "")
            for index, column in enumerate(columns)
        )
        lines.append(")")
        return lines

    return ["insert into " + sql_expr(target, options)]


def format_values_lines(
    tuples: list[exp.Expression], options: FormatOptions, force_multiline: bool = False
) -> list[str]:
    force_multiline = force_multiline or any(
        len("    " + format_tuple_values(tuple_expr, options)) > options.short_query_max_width
        for tuple_expr in tuples
    )

    if len(tuples) == 1:
        compact = format_tuple_values(tuples[0], options)
        line = "values " + compact
        if not force_multiline and len(line) <= options.short_query_max_width:
            return [line]
        lines = format_tuple_values_multiline(tuples[0], options, "")
        lines[0] = "values " + lines[0]
        return lines

    lines = ["values"]
    for index, tuple_expr in enumerate(tuples):
        suffix = "," if index < len(tuples) - 1 else ""
        compact = "    " + format_tuple_values(tuple_expr, options) + suffix
        if not force_multiline and len(compact) <= options.short_query_max_width:
            lines.append(compact)
            continue

        tuple_lines = format_tuple_values_multiline(tuple_expr, options, "    ")
        tuple_lines[-1] += suffix
        lines.extend(tuple_lines)
    return lines


def format_tuple_values(tuple_expr: exp.Expression, options: FormatOptions) -> str:
    if isinstance(tuple_expr, exp.Tuple):
        return "(" + ", ".join(sql_expr(item, options) for item in tuple_expr.expressions) + ")"
    return sql_expr(tuple_expr, options)


def format_tuple_values_multiline(
    tuple_expr: exp.Expression, options: FormatOptions, prefix: str
) -> list[str]:
    if not isinstance(tuple_expr, exp.Tuple):
        return [prefix + sql_expr(tuple_expr, options)]

    values = [sql_expr(item, options) for item in tuple_expr.expressions]
    lines = [prefix + "("]
    lines.extend(
        prefix + "    " + value + ("," if index < len(values) - 1 else "")
        for index, value in enumerate(values)
    )
    lines.append(prefix + ")")
    return lines


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

    first, *rest = expressions
    lines = ["returning " + first + ","]
    lines.extend(
        " " * len("returning ") + item + ("," if index < len(rest) - 1 else "")
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
