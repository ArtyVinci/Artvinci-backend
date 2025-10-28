"""
Admin integration note:
This project uses MongoEngine for data storage. The Artwork model in this app is a MongoEngine Document.
Django's admin doesn't manage MongoEngine documents out of the box. If you want admin support, consider
using a third-party integration (like django-mongoengine) or implement a custom admin interface.

For now this file is intentionally left minimal to avoid runtime errors in the default Django admin.
"""

