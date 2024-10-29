===========
Get Started
===========

.. _installation:

Installation
============

To install ``django_documentdb`` use one of the following methods:

Using pip
-----------

You can install ``django_documentdb`` with ``pip``:

.. code-block:: bash

   pip install django_documentdb

Using Poetry
------------

If you're using Poetry to manage your dependencies, you can add ``django_documentdb`` to your project with the following command:

.. code-block:: bash

   poetry add django_documentdb

Project setup
=============

You can set up a new Django project using ready-to-use templates or integrate ``django_documentdb`` into an existing project.

**Starting from Scratch**: Create a new Django project configured for MongoDB using the provided project template:

.. code-block:: bash

   django-admin startproject mysite --template https://github.com/mongodb-labs/django-mongodb-project/archive/refs/heads/5.0.x.zip

This template includes the necessary settings to use ``django_documentdb``, including the required ``DEFAULT_AUTO_FIELD``.

For detailed configuration instructions, refer to the :ref:`configuration` section in the documentation. This section covers:

- Setting the default primary key field.
- Configuring migrations for your applications.
- Setting up the ``DATABASES`` configuration.

If you already have a Django project and want to integrate ``django_documentdb``, please consult the configuration instructions for modifying your existing setup.

Next Steps
==========

Explore the following topics to learn more about ``django_documentdb``:

- :ref:`configuration`: Detailed instructions for setting up and configuring ``django_documentdb``.
- :ref:`api_references`: For detailed information on all classes and methods, see the API reference.
