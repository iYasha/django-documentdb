.. _introduction:

Introduction
===================================

This project, **django-documentdb**, is a fork of the original **django-mongodb** repository, which was developed and maintained by the MongoDB Python Team. The primary purpose of this fork is to enhance compatibility with **AWS DocumentDB**, a MongoDB-compatible database service provided by Amazon Web Services. To accommodate the differences between DocumentDB and MongoDB’s API support, specific adjustments have been implemented to ensure seamless functionality within DocumentDB.

We encourage users to provide feedback and report any issues as we continue to improve the library. You can share your thoughts, suggestions, or report problems on our `GitHub Issues page <https://github.com/iYasha/django-documentdb/issues>`_

Key Features
------------

- **ObjectIdAutoField Support**: All models are configured to use `ObjectIdAutoField` as the default primary key field.
- **Custom AppConfig**: Easily create custom application configurations to ensure compatibility with DocumentDB.
- **Migration Management**: Configure migrations for third-party and contrib apps specific to MongoDB.
- **Integration with Django**: Designed to work seamlessly with existing Django projects, offering an easy transition to using DocumentDB.

As you start exploring **django_documentdb**, please refer to the :ref:`installation` and :ref:`configuration` sections for detailed setup instructions.
