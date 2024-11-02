FROM python:3.11.10

ENV PYTHONUNBUFFERED 1

RUN apt-get update && apt-get install -y git libmemcached-dev

WORKDIR /package-test/

COPY . django-documentdb
COPY ./tests/django django
COPY .github/workflows/documentdb_settings.py django/tests/
COPY rds-combined-ca-bundle.pem /package-test/rds-combined-ca-bundle.pem
RUN find django -type f -exec sed -i 's/django_mongodb/django_documentdb/g' {} +

RUN pip install -e django-documentdb
RUN pip install -e django
RUN pip install -r django/tests/requirements/py3.txt


CMD ["python", "django/tests/runtests.py", "--settings", "documentdb_settings", "-v", "2", "aggregation"]
