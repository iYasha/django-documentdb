# DocumentDB/MongoDB backend for Django

This project, **django-documentdb**, is a fork of the original **django-mongodb** repository, which was developed and maintained by the MongoDB Python Team. The primary purpose of this fork is to enhance compatibility with **AWS DocumentDB**, a MongoDB-compatible database service provided by Amazon Web Services. To accommodate the differences between DocumentDB and MongoDB’s API support, specific adjustments have been implemented to ensure seamless functionality within DocumentDB.

We encourage users to provide feedback and report any issues as we continue to improve the library. You can share your thoughts, suggestions, or report problems on our [GitHub Issues page](https://github.com/iYasha/django-documentdb/issues)

## Documentation
For full documentation, including installation, configuration, etc. Please see https://django-documentdb.readthedocs.io/

## Installation

To install `django_documentdb`, use one of the following methods:

### Using pip

You can install `django_documentdb` with:

```bash
pip install django_documentdb
```

### Using Poetry

If you're using Poetry to manage your dependencies, you can add `django_documentdb` to your project with:

```bash
poetry add django_documentdb
```

## Notes on Django QuerySets

django-documentdb uses own QuerySet implementation (`DocumentQuerySet`) if you inherit your models from `DocumentModel` class.

### Example:

```python
from django_documentdb.models import DocumentModel
from django_documentdb import fields
from django.db import models


class TestModel(DocumentModel):
    _id = fields.ObjectIdAutoField(primary_key=True)
    text_value = models.CharField(max_length=100, null=True)
    number_value = models.FloatField(null=True)

    class Meta:
        db_table = "test_db"
```

### Available options with `DocumentQuerySet`:

* `QuerySet.explain()` supports the [`comment` and `verbosity` options](
  https://www.mongodb.com/docs/manual/reference/command/explain/#command-fields).

   Example: `QuerySet.explain(comment="...", verbosity="...")`

   Valid values for `verbosity` are `"queryPlanner"` (default),
   `"executionStats"`, and `"allPlansExecution"`.
* `DocumentQuerySet.index_hint(index_name)` - allows to specify index hint for query.

## Known issues and limitations

- The following `QuerySet` methods aren't supported:
  - `bulk_update()`
  - `dates()`
  - `datetimes()`
  - `distinct()`
  - `extra()`
  - `prefetch_related()`

- `QuerySet.delete()` and `update()` do not support queries that span multiple
  collections.

- `DateTimeField` doesn't support microsecond precision, and correspondingly,
  `DurationField` stores milliseconds rather than microseconds.

- The following database functions aren't supported:
    - `Chr`
    - `ExtractQuarter`
    - `MD5`
    - `Now`
    - `Ord`
    - `Pad`
    - `Repeat`
    - `Reverse`
    - `Right`
    - `SHA1`, `SHA224`, `SHA256`, `SHA384`, `SHA512`
    - `Sign`
    - `TruncDate`
    - `TruncTime`

- The `tzinfo` parameter of the `Trunc` database functions doesn't work
  properly because MongoDB converts the result back to UTC.

- When querying `JSONField`:
  - There is no way to distinguish between a JSON "null" (represented by
    `Value(None, JSONField())`) and a SQL null (queried using the `isnull`
    lookup). Both of these queries return both of these nulls.
  - Some queries with `Q` objects, e.g. `Q(value__foo="bar")`, don't work
    properly, particularly with `QuerySet.exclude()`.
  - Filtering for a `None` key, e.g. `QuerySet.filter(value__j=None)`
    incorrectly returns objects where the key doesn't exist.
  - You can study the skipped tests in `DatabaseFeatures.django_test_skips` for
    more details on known issues.

- Due to the lack of ability to introspect MongoDB collection schema,
  `migrate --fake-initial` isn't supported.

## Forked Project

This project, **django-documentdb**, is a fork of the original **django-mongodb** library, which aimed to integrate MongoDB with Django. The fork was created to enhance compatibility with AWS DocumentDB, addressing the limitations of its API support while maintaining the core functionalities of the original library. We appreciate the work of the MongoDB Python Team and aim to build upon their foundation to better serve users needing DocumentDB integration.
