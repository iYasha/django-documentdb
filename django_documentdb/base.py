import warnings

from django.db.backends.base.base import BaseDatabaseWrapper
from django.db.backends.signals import connection_created
from pymongo.collection import Collection
from pymongo.mongo_client import MongoClient

from . import dbapi as Database
from .client import DatabaseClient
from .creation import DatabaseCreation
from .features import DatabaseFeatures
from .introspection import DatabaseIntrospection
from .operations import DatabaseOperations
from .query_utils import regex_match
from .schema import DatabaseSchemaEditor
from .utils import IndexNotUsedWarning, OperationDebugWrapper

# ignore warning from pymongo about DocumentDB
warnings.filterwarnings("ignore", "You appear to be connected to a DocumentDB cluster", UserWarning)


class Cursor:
    """A "nodb" cursor that does nothing except work on a context manager."""

    def __enter__(self):
        pass

    def __exit__(self, exception_type, exception_value, exception_traceback):
        pass


class DatabaseWrapper(BaseDatabaseWrapper):
    data_types = {
        "AutoField": "int",
        "BigAutoField": "long",
        "BinaryField": "binData",
        "BooleanField": "bool",
        "CharField": "string",
        "DateField": "date",
        "DateTimeField": "date",
        "DecimalField": "decimal",
        "DurationField": "long",
        "FileField": "string",
        "FilePathField": "string",
        "FloatField": "double",
        "IntegerField": "int",
        "BigIntegerField": "long",
        "GenericIPAddressField": "string",
        "JSONField": "object",
        "OneToOneField": "int",
        "PositiveBigIntegerField": "int",
        "PositiveIntegerField": "long",
        "PositiveSmallIntegerField": "int",
        "SlugField": "string",
        "SmallAutoField": "int",
        "SmallIntegerField": "int",
        "TextField": "string",
        "TimeField": "date",
        "UUIDField": "string",
    }
    # Django uses these operators to generate SQL queries before it generates
    # MQL queries.
    operators = {
        "exact": "= %s",
        "iexact": "= UPPER(%s)",
        "contains": "LIKE %s",
        "icontains": "LIKE UPPER(%s)",
        "regex": "~ %s",
        "iregex": "~* %s",
        "gt": "> %s",
        "gte": ">= %s",
        "lt": "< %s",
        "lte": "<= %s",
        "startswith": "LIKE %s",
        "endswith": "LIKE %s",
        "istartswith": "LIKE UPPER(%s)",
        "iendswith": "LIKE UPPER(%s)",
    }
    # As with `operators`, these patterns are used to generate SQL before MQL.
    pattern_esc = "%%"
    pattern_ops = {
        "contains": "LIKE '%%' || {} || '%%'",
        "icontains": "LIKE '%%' || UPPER({}) || '%%'",
        "startswith": "LIKE {} || '%%'",
        "istartswith": "LIKE UPPER({}) || '%%'",
        "endswith": "LIKE '%%' || {}",
        "iendswith": "LIKE '%%' || UPPER({})",
    }

    def _isnull_operator(a, b):
        if b:
            return {a: None}

        warnings.warn("You're using $ne, index will not be used", IndexNotUsedWarning, stacklevel=1)
        return {a: {"$ne": None}}

    mongo_operators = {
        # Where a = field_name, b = value
        "exact": lambda a, b: {a: b},
        "gt": lambda a, b: {a: {"$gt": b}},
        "gte": lambda a, b: {a: {"$gte": b}},
        "lt": lambda a, b: {a: {"$lt": b}},
        "lte": lambda a, b: {a: {"$lte": b}},
        "in": lambda a, b: {a: {"$in": b}},
        "isnull": _isnull_operator,
        "range": lambda a, b: {
            "$and": [
                {"$or": [{a: {"$gte": b[0]}}, {a: None}]},
                {"$or": [{a: {"$lte": b[1]}}, {a: None}]},
            ]
        },
        "iexact": lambda a, b: regex_match(a, f"^{b}$", insensitive=True),
        "startswith": lambda a, b: regex_match(a, f"^{b}"),
        "istartswith": lambda a, b: regex_match(a, f"^{b}", insensitive=True),
        "endswith": lambda a, b: regex_match(a, f"{b}$"),
        "iendswith": lambda a, b: regex_match(a, f"{b}$", insensitive=True),
        "contains": lambda a, b: regex_match(a, b),
        "icontains": lambda a, b: regex_match(a, b, insensitive=True),
        "regex": lambda a, b: regex_match(a, b),
        "iregex": lambda a, b: regex_match(a, b, insensitive=True),
    }

    display_name = "DocumentDB"
    vendor = "documentdb"
    Database = Database
    SchemaEditorClass = DatabaseSchemaEditor
    client_class = DatabaseClient
    creation_class = DatabaseCreation
    features_class = DatabaseFeatures
    introspection_class = DatabaseIntrospection
    ops_class = DatabaseOperations

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.connected = False
        del self.connection

    def get_collection(self, name, **kwargs):
        collection = Collection(self.database, name, **kwargs)
        if self.queries_logged:
            collection = OperationDebugWrapper(self, collection)
        return collection

    def get_database(self):
        if self.queries_logged:
            return OperationDebugWrapper(self)
        return self.database

    def __getattr__(self, attr):
        """
        Connect to the database the first time `connection` or `database` are
        accessed.
        """
        if attr in ["connection", "database"]:
            assert not self.connected
            self._connect()
            return getattr(self, attr)
        raise AttributeError(attr)

    def _connect(self):
        settings_dict = self.settings_dict
        self.connection = MongoClient(
            host=settings_dict["HOST"] or None,
            port=int(settings_dict.get("PORT") or 27017),
            username=settings_dict.get("USER"),
            password=settings_dict.get("PASSWORD"),
            **settings_dict["OPTIONS"],
        )
        db_name = settings_dict["NAME"]
        if db_name:
            self.database = self.connection[db_name]

        self.connected = True
        connection_created.send(sender=self.__class__, connection=self)

    def _commit(self):
        pass

    def _rollback(self):
        pass

    def close(self):
        if self.connected:
            self.connection.close()
            del self.connection
            del self.database
            self.connected = False

    def cursor(self):
        return Cursor()

    def get_database_version(self):
        """Return a tuple of the database's version."""
        return tuple(self.connection.server_info()["versionArray"])
