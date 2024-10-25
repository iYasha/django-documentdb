import datetime
import warnings
from decimal import Decimal
from uuid import UUID

from bson import Decimal128
from django.core.exceptions import EmptyResultSet, FullResultSet
from django.db import NotSupportedError
from django.db.models.expressions import (
    Case,
    Col,
    CombinedExpression,
    Exists,
    ExpressionWrapper,
    F,
    NegatedExpression,
    OrderBy,
    RawSQL,
    Ref,
    ResolvedOuterRef,
    Star,
    Subquery,
    Value,
    When,
)
from django.db.models.sql import Query

from django_documentdb.utils import IndexNotUsedWarning


def case(self, compiler, connection):
    case_parts = []
    for case in self.cases:
        case_mql = {}
        try:
            case_mql["case"] = case.as_mql(compiler, connection)
        except EmptyResultSet:
            continue
        except FullResultSet:
            default_mql = case.result.as_mql(compiler, connection)
            break
        case_mql["then"] = case.result.as_mql(compiler, connection)
        case_parts.append(case_mql)
    else:
        default_mql = self.default.as_mql(compiler, connection)
    if not case_parts:
        return default_mql
    return {
        "$switch": {
            "branches": case_parts,
            "default": default_mql,
        }
    }


def col(self, compiler, connection):  # noqa: ARG001
    # If the column is part of a subquery and belongs to one of the parent
    # queries, it will be stored for reference using $let in a $lookup stage.
    if (
        self.alias not in compiler.query.alias_refcount
        or compiler.query.alias_refcount[self.alias] == 0
    ):
        try:
            index = compiler.column_indices[self]
        except KeyError:
            index = len(compiler.column_indices)
            compiler.column_indices[self] = index
        return f"$${compiler.PARENT_FIELD_TEMPLATE.format(index)}"  # TODO: Potential bug
    # Add the column's collection's alias for columns in joined collections.
    prefix = f"{self.alias}." if self.alias != compiler.collection_name else ""
    return f"{prefix}{self.target.column}"


def combined_expression(self, compiler, connection):
    expressions = [
        f"${self.lhs.as_mql(compiler, connection)}"
        if isinstance(self.lhs, Col)
        else self.lhs.as_mql(compiler, connection),
        f"${self.rhs.as_mql(compiler, connection)}"
        if isinstance(self.rhs, Col)
        else self.rhs.as_mql(compiler, connection),
    ]
    return connection.ops.combine_expression(self.connector, expressions)


def expression_wrapper(self, compiler, connection):
    return self.expression.as_mql(compiler, connection)


def f(self, compiler, connection):  # noqa: ARG001
    return f"${self.name}"


def negated_expression(self, compiler, connection):
    warnings.warn("You're using $not, index will not be used.", IndexNotUsedWarning, stacklevel=1)

    return {"$not": expression_wrapper(self, compiler, connection)}


def order_by(self, compiler, connection):
    return self.expression.as_mql(compiler, connection)


def query(self, compiler, connection, lookup_name=None):
    subquery_compiler = self.get_compiler(connection=connection)
    subquery_compiler.pre_sql_setup(with_col_aliases=False)
    columns = subquery_compiler.get_columns()
    field_name, expr = columns[0]
    subquery = subquery_compiler.build_query(
        columns
        if subquery_compiler.query.annotations or not subquery_compiler.query.default_cols
        else None
    )
    table_output = f"__subquery{len(compiler.subqueries)}"
    from_table = next(
        e.table_name for alias, e in self.alias_map.items() if self.alias_refcount[alias]
    )
    # To perform a subquery, a $lookup stage that escapsulates the entire
    # subquery pipeline is added. The "let" clause defines the variables
    # needed to bridge the main collection with the subquery.
    subquery.subquery_lookup = {
        "as": table_output,
        "from": from_table,
        "let": {
            compiler.PARENT_FIELD_TEMPLATE.format(i): col.as_mql(compiler, connection)
            for col, i in subquery_compiler.column_indices.items()
        },
    }
    # The result must be a list of values. The output is compressed with an
    # aggregation pipeline.
    if lookup_name in ("in", "range"):
        if subquery.aggregation_pipeline is None:
            subquery.aggregation_pipeline = []
        subquery.aggregation_pipeline.extend(
            [
                {
                    "$facet": {
                        "group": [
                            {
                                "$group": {
                                    "_id": None,
                                    "tmp_name": {
                                        "$addToSet": expr.as_mql(subquery_compiler, connection)
                                    },
                                }
                            }
                        ]
                    }
                },
                {
                    "$project": {
                        field_name: {
                            "$ifNull": [
                                {
                                    "$getField": {
                                        "input": {"$arrayElemAt": ["$group", 0]},
                                        "field": "tmp_name",
                                    }
                                },
                                [],
                            ]
                        }
                    }
                },
            ]
        )
        # Erase project_fields since the required value is projected above.
        subquery.project_fields = None
    compiler.subqueries.append(subquery)
    return f"${table_output}.{field_name}"


def raw_sql(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError("RawSQL is not supported on MongoDB.")


def ref(self, compiler, connection):  # noqa: ARG001
    prefix = (
        f"{self.source.alias}."
        if isinstance(self.source, Col) and self.source.alias != compiler.collection_name
        else ""
    )
    return f"${prefix}{self.refs}"


def star(self, compiler, connection):  # noqa: ARG001
    return {"$literal": True}


def subquery(self, compiler, connection, lookup_name=None):
    return self.query.as_mql(compiler, connection, lookup_name=lookup_name)


def exists(self, compiler, connection, lookup_name=None):
    try:
        lhs_mql = subquery(self, compiler, connection, lookup_name=lookup_name)
    except EmptyResultSet:
        return Value(False).as_mql(compiler, connection)
    return connection.mongo_operators["isnull"](lhs_mql, False)


def when(self, compiler, connection):
    return self.condition.as_mql(compiler, connection)


def value(self, compiler, connection):  # noqa: ARG001
    value = self.value
    if isinstance(value, Decimal):
        value = Decimal128(value)
    elif isinstance(value, datetime.date):
        # Turn dates into datetimes since BSON doesn't support dates.
        value = datetime.datetime.combine(value, datetime.datetime.min.time())
    elif isinstance(value, datetime.time):
        # Turn times into datetimes since BSON doesn't support times.
        value = datetime.datetime.combine(datetime.datetime.min.date(), value)
    elif isinstance(value, datetime.timedelta):
        # DurationField stores milliseconds rather than microseconds.
        value /= datetime.timedelta(milliseconds=1)
    elif isinstance(value, UUID):
        value = value.hex
    return {"$literal": value}


def register_expressions():
    Case.as_mql = case
    Col.as_mql = col
    CombinedExpression.as_mql = combined_expression
    Exists.as_mql = exists
    ExpressionWrapper.as_mql = expression_wrapper
    F.as_mql = f
    NegatedExpression.as_mql = negated_expression
    OrderBy.as_mql = order_by
    Query.as_mql = query
    RawSQL.as_mql = raw_sql
    Ref.as_mql = ref
    ResolvedOuterRef.as_mql = ResolvedOuterRef.as_sql
    Star.as_mql = star
    Subquery.as_mql = subquery
    When.as_mql = when
    Value.as_mql = value