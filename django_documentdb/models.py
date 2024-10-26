from django.db import models


class DocumentQuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def index_hint(self, index_name: str) -> "DocumentQuerySet":
        self.query._index_hint = index_name
        return self


class DocumentModel(models.Model):
    objects = DocumentQuerySet.as_manager()

    class Meta:
        abstract = True
        db_table = None
