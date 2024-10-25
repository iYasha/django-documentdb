## About This Fork

This project, **django-documentdb**, is a fork of the original **django-mongodb** repository, which was developed and maintained by the MongoDB Python Team. The primary purpose of this fork is to add compatibility with **AWS DocumentDB**, a MongoDB-compatible database service by Amazon Web Services. Due to differences between DocumentDB and MongoDB’s API support, specific adjustments have been made to enable functionality within DocumentDB.

### Why Fork?
AWS DocumentDB currently supports a subset of MongoDB's API. Some features, such as `$expr` queries, are either partially supported or unsupported, leading to limitations when using libraries built for MongoDB directly. Given that the original `django-mongodb` repository was optimized for full MongoDB support, this fork introduces compatibility adjustments specifically for DocumentDB.

### Notice of Modification

All files in this repository may have been modified from the original code. These modifications are provided under the terms of the Apache License 2.0 and comply with the original licensing requirements. For details on the original license, see `LICENSE`.

### Acknowledgments

We extend our thanks to the MongoDB Python Team for their foundational work on `django-mongodb`. Their efforts have been essential in making Django and MongoDB integration accessible and effective. This fork maintains their original Apache 2.0 license, as well as their attributions, while aiming to support new use cases with DocumentDB.

For additional information on third-party libraries or resources used, please see the `THIRD-PARTY-NOTICES` file.

### License

This project is distributed under the Apache License 2.0, consistent with the original `django-mongodb` repository. All original licenses and attributions have been retained as required.
