.. _configuration:

=============
Configuration
=============

This section provides guidance on how to configure your Django project to use ``django-documentdb``.

Specifying the Default Primary Key Field
=========================================

In your Django settings, you must specify that all models should use ``ObjectIdAutoField``.

Change the following line in ``settings.py``:

.. code-block:: python

    DEFAULT_AUTO_FIELD = "django_documentdb.fields.ObjectIdAutoField"

However, this setting won't override any apps that have an ``AppConfig`` that specifies ``default_auto_field``. For those apps, you'll need to create a custom ``AppConfig``. For example:

.. code-block:: python

    from django.contrib.admin.apps import AdminConfig
    from django.contrib.auth.apps import AuthConfig
    from django.contrib.contenttypes.apps import ContentTypesConfig


    class MongoAdminConfig(AdminConfig):
        default_auto_field = "django_documentdb.fields.ObjectIdAutoField"


    class MongoAuthConfig(AuthConfig):
        default_auto_field = "django_documentdb.fields.ObjectIdAutoField"


    class MongoContentTypesConfig(ContentTypesConfig):
        default_auto_field = "django_documentdb.fields.ObjectIdAutoField"

Each app reference in the ``INSTALLED_APPS`` setting must point to the corresponding ``AppConfig``. For example, instead of ``'django.contrib.admin'``, use ``'<project_name>.apps.MongoAdminConfig``.

Configuring Migrations
======================

Because all models must use ``ObjectIdAutoField``, each third-party and contrib app you use needs to have its own migrations specific to DocumentDB/MongoDB. In the project template, ``settings.py`` specifies:

.. code-block:: python

    MIGRATION_MODULES = {
        "admin": "mongo_migrations.admin",
        "auth": "mongo_migrations.auth",
        "contenttypes": "mongo_migrations.contenttypes",
    }

You can generate migrations if you're setting things up manually or need to create migrations for third-party apps. For example:

.. code-block:: bash

    python manage.py makemigrations admin auth contenttypes

Creating Django Applications
============================

Whenever you run ``python manage.py startapp``, you must remove the line:

.. code-block:: python

    default_auto_field = "django.db.models.BigAutoField"

from the new application's ``apps.py`` file, or change it to reference ``ObjectIdAutoField``:

.. code-block:: python

    default_auto_field = "django_documentdb.fields.ObjectIdAutoField"

Alternatively, you can use the following ``startapp`` template that includes this change:

.. code-block:: bash

    python manage.py startapp myapp --template https://github.com/mongodb-labs/django-mongodb-app/archive/refs/heads/5.0.x.zip

(where "5.0" matches the version of Django that you're using.)

Configuring the ``DATABASES`` Setting
=====================================

After you've set up a project, configure Django's ``DATABASES`` setting as follows:

.. code-block:: python

    DATABASES = {
        "default": {
            "ENGINE": "django_documentdb",
            "NAME": "my_database",
            "USER": "my_user",
            "PASSWORD": "my_password",
            "OPTIONS": {...},
        },
    }

The ``OPTIONS`` field is an optional dictionary of parameters that will be passed to `MongoClient <https://pymongo.readthedocs.io/en/stable/api/pymongo/mongo_client.html>`_.

DocumentDB Connection Options
-----------------------------

When connecting to DocumentDB, you can specify additional connection options in the ``OPTIONS`` dictionary. For example:

.. code-block:: python

    DATABASES = {
        "default": {
            # database settings
            "OPTIONS": {
                # Other options
                "authSource": "admin",
                "tls": True,
                "tlsCAFile": "/path/to/ca.pem",
                "retryWrites": False,
            },
        },
    }

Connection Pooling Options
--------------------------

Connection pooling options can also be specified in the ``OPTIONS`` dictionary. For example:

.. code-block:: python

    DATABASES = {
        "default": {
            # database settings
            "OPTIONS": {
                # Other options
                "maxPoolSize": 30,
                "maxIdleTimeMS": 10 * 60 * 1000,
            }
        },
    }

Congratulations, your project is ready to go!
