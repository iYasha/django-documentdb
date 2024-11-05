import typing
import warnings
from functools import reduce, wraps
from operator import add as add_operator

from django.core.exceptions import EmptyResultSet, FullResultSet
from django.db import DatabaseError, IntegrityError, NotSupportedError
from django.db.models.expressions import Case, When
from django.db.models.functions import Mod
from django.db.models.lookups import Exact
from django.db.models.sql.constants import INNER
from django.db.models.sql.datastructures import Join
from django.db.models.sql.where import AND, OR, XOR, ExtraWhere, NothingNode, WhereNode
from pymongo.errors import BulkWriteError, DuplicateKeyError, PyMongoError
from pymongo.synchronous.cursor import Cursor
from pymongo.typings import _DocumentType

if typing.TYPE_CHECKING:
    from django_documentdb.base import DatabaseWrapper
    from django_documentdb.compiler import SQLCompiler
from django_documentdb.utils import IndexNotUsedWarning


def wrap_database_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except BulkWriteError as e:
            if "E11000 duplicate key error" in str(e):
                raise IntegrityError from e
            raise
        except DuplicateKeyError as e:
            raise IntegrityError from e
        except PyMongoError as e:
            raise DatabaseError from e

    return wrapper


class MongoQuery:
    """
    Compilers build a MongoQuery when they want to fetch some data. They work
    by first allowing sql.compiler.SQLCompiler to partly build a sql.Query,
    constructing a MongoQuery query on top of it, and then iterating over its
    results.

    This class provides a framework for converting the SQL constraint tree
    built by Django to a "representation" more suitable for MongoDB.
    """

    def __init__(self, compiler: "SQLCompiler"):
        self.compiler = compiler
        self.connection = compiler.connection
        self.ops = compiler.connection.ops
        self.query = compiler.query
        self._negated = False
        self.ordering = []
        self.collection = self.compiler.collection
        self.collection_name = self.compiler.collection_name
        self.mongo_query = getattr(compiler.query, "raw_query", {})
        self.subqueries = None
        self.lookup_pipeline = None
        self.project_fields = None
        self.aggregation_pipeline = compiler.aggregation_pipeline
        self.extra_fields = None
        self.combinator_pipeline = None
        # $lookup stage that encapsulates the pipeline for performing a nested
        # subquery.
        self.subquery_lookup = None

    def __repr__(self):
        return f"<MongoQuery: {self.mongo_query!r} ORDER {self.ordering!r}>"

    @wrap_database_errors
    def delete(self):
        """Execute a delete query."""
        if self.compiler.subqueries:
            raise NotSupportedError("Cannot use QuerySet.delete() when a subquery is required.")
        return self.collection.delete_many(self.mongo_query).deleted_count

    @wrap_database_errors
    def get_cursor(self) -> Cursor[_DocumentType]:
        """
        Return a pymongo CommandCursor that can be iterated on to give the
        results of the query.
        """
        if self.is_simple_lookup:
            pipeline = self.build_simple_lookup()
            return self.collection.find(**pipeline)

        pipeline = self.get_pipeline()
        options = {}
        if hasattr(self.query, "_index_hint"):
            options["hint"] = self.query._index_hint
        return self.collection.aggregate(pipeline, **options)

    @property
    def is_simple_lookup(self) -> bool:
        return bool(
            self.mongo_query
            and not self.lookup_pipeline
            and not self.aggregation_pipeline
            and not self.subqueries
            and not self.combinator_pipeline
            and not self.extra_fields
            and not self.subquery_lookup
        )

    def build_simple_lookup(self) -> dict:
        pipeline = {}
        if self.mongo_query:
            pipeline["filter"] = self.mongo_query
        else:
            raise ValueError("No lookup pipeline or query found.")
        if self.project_fields:
            pipeline["projection"] = self.project_fields
        if self.ordering:
            pipeline["sort"] = self.ordering
        if self.query.low_mark > 0:
            pipeline["skip"] = self.query.low_mark
        if self.query.high_mark is not None:
            pipeline["limit"] = self.query.high_mark - self.query.low_mark
        if hasattr(self.query, "_index_hint"):
            pipeline["hint"] = self.query._index_hint
        return pipeline

    def get_pipeline(self):
        pipeline = []
        if self.lookup_pipeline:
            pipeline.extend(self.lookup_pipeline)
        for query in self.subqueries or ():
            pipeline.extend(query.get_pipeline())
        if self.mongo_query:
            pipeline.append({"$match": self.mongo_query})
        if self.aggregation_pipeline:
            pipeline.extend(self.aggregation_pipeline)
        if self.project_fields:
            pipeline.append({"$project": self.project_fields})
        if self.combinator_pipeline:
            pipeline.extend(self.combinator_pipeline)
        if self.extra_fields:
            pipeline.append({"$addFields": self.extra_fields})
        if self.ordering:
            pipeline.append({"$sort": self.ordering})
        if self.query.low_mark > 0:
            pipeline.append({"$skip": self.query.low_mark})
        if self.query.high_mark is not None:
            pipeline.append({"$limit": self.query.high_mark - self.query.low_mark})
        if self.subquery_lookup:
            table_output = self.subquery_lookup["as"]
            pipeline = [
                {"$lookup": {**self.subquery_lookup, "pipeline": pipeline}},
                {
                    "$set": {
                        table_output: {
                            "$cond": {
                                "if": {
                                    "$or": [
                                        {"$eq": [{"$type": f"${table_output}"}, "missing"]},
                                        {"$eq": [{"$size": f"${table_output}"}, 0]},
                                    ]
                                },
                                "then": {},
                                "else": {"$arrayElemAt": [f"${table_output}", 0]},
                            }
                        }
                    }
                },
            ]
        return pipeline


def extra_where(self, compiler, connection):  # noqa: ARG001
    raise NotSupportedError("QuerySet.extra() is not supported on MongoDB.")


def join(self: Join, compiler: "SQLCompiler", connection: "DatabaseWrapper"):
    lhs_fields = []
    rhs_fields = []

    # Add a join condition for each pair of joining fields.
    for lhs, rhs in self.join_fields:
        lhs, rhs = connection.ops.prepare_join_on_clause(
            self.parent_alias, lhs, compiler.collection_name, rhs
        )
        lhs_fields.append(lhs.as_mql(compiler, connection))
        rhs_fields.append(rhs.as_mql(compiler, connection))

    # Create lookups for each pair of fields.
    lookup_pipeline = [
        {
            "$lookup": {
                "from": self.table_name,  # The right-hand table to join.
                "localField": lhs_field,  # Field from the main collection.
                "foreignField": rhs_field,  # Field from the joined collection.
                "as": self.table_alias,  # Output array field.
            }
        }
        for lhs_field, rhs_field in zip(lhs_fields, rhs_fields, strict=True)
    ]

    # Handle any extra conditions if applicable
    if self.join_field.get_extra_restriction(self.table_alias, self.parent_alias):
        extra_condition = self.join_field.get_extra_restriction(
            self.table_alias, self.parent_alias
        ).as_mql(compiler, connection)
        lookup_pipeline.append({"$match": extra_condition})

    # To avoid missing data when using $unwind, an empty collection is added if
    # the join isn't an inner join. For inner joins, rows with empty arrays are
    # removed, as $unwind unrolls or unnests the array and removes the row if
    # it's empty. This is the expected behavior for inner joins. For left outer
    # joins (LOUTER), however, an empty collection is returned.
    if self.join_type != INNER:
        lookup_pipeline.append(
            {
                "$addFields": {
                    self.table_alias: {
                        "$cond": {
                            "if": {
                                "$or": [
                                    {"$eq": [{"$type": f"${self.table_alias}"}, "missing"]},
                                    {"$eq": [{"$size": f"${self.table_alias}"}, 0]},
                                ]
                            },
                            "then": [{}],
                            "else": f"${self.table_alias}",
                        }
                    }
                }
            }
        )

    lookup_pipeline.append(
        {
            "$unwind": {
                "path": f"${self.table_alias}",
                "preserveNullAndEmptyArrays": True,  # Preserve documents without matches
            }
        }
    )

    return lookup_pipeline


def where_node(self, compiler, connection):
    if self.connector == AND:
        full_needed, empty_needed = len(self.children), 1
    else:
        full_needed, empty_needed = 1, len(self.children)

    if self.connector == AND:
        operator = "$and"
    elif self.connector == XOR:
        # MongoDB doesn't support $xor, so convert:
        #   a XOR b XOR c XOR ...
        # to:
        #   (a OR b OR c OR ...) AND MOD(a + b + c + ..., 2) == 1
        # The result of an n-ary XOR is true when an odd number of operands
        # are true.
        lhs = self.__class__(self.children, OR)
        rhs_sum = reduce(
            add_operator,
            (Case(When(c, then=1), default=0) for c in self.children),
        )
        if len(self.children) > 2:
            rhs_sum = Mod(rhs_sum, 2)
        rhs = Exact(1, rhs_sum)
        return self.__class__([lhs, rhs], AND, self.negated).as_mql(compiler, connection)
    else:
        operator = "$or"

    children_mql = []
    for child in self.children:
        try:
            mql = child.as_mql(compiler, connection)
        except EmptyResultSet:
            empty_needed -= 1
        except FullResultSet:
            full_needed -= 1
        else:
            if mql:
                children_mql.append(mql)
            else:
                full_needed -= 1

        if empty_needed == 0:
            raise (FullResultSet if self.negated else EmptyResultSet)
        if full_needed == 0:
            raise (EmptyResultSet if self.negated else FullResultSet)

    if len(children_mql) == 1:
        mql = children_mql[0]
    elif len(children_mql) > 1:
        mql = {operator: children_mql} if children_mql else {}
    else:
        mql = {}

    if not mql:
        raise FullResultSet

    if self.negated and mql:
        warnings.warn(
            "You're using $not, index will not be used.", IndexNotUsedWarning, stacklevel=1
        )

        mql = {"$not": mql}

    return mql


def register_nodes():
    ExtraWhere.as_mql = extra_where
    Join.as_mql = join
    NothingNode.as_mql = NothingNode.as_sql
    WhereNode.as_mql = where_node
