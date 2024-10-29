==========
Debugging
==========

This section provides guidance on how to debug your Django project when using ``django-documentdb``.

Enable query logging
=====================

To enable query logging change the following line in ``settings.py``:

.. code-block:: python

    DEBUG = True

    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
            },
        },
        "loggers": {
            "django.db.backends": {
                "handlers": ["console"],
                "level": "DEBUG",  # Set log level to DEBUG
            },
        },
    }
