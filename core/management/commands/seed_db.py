import os
import json
from django.core.management.base import BaseCommand
from urllib.parse import urlparse
import pymongo


class Command(BaseCommand):
    help = 'Seed the MongoDB database with a minimal sample document (safe to run multiple times)'

    def handle(self, *args, **options):
        mongo_uri = os.environ.get('MONGO_URI') or os.environ.get('MONGODB_URI')
        db_name = os.environ.get('MONGO_DB_NAME') or os.environ.get('MONGODB_DATABASE') or 'artvinci_prod'

        if not mongo_uri:
            self.stdout.write(self.style.ERROR('MONGO_URI environment variable not found. Aborting seed.'))
            return

        try:
            client = pymongo.MongoClient(mongo_uri, tlsAllowInvalidCertificates=True)
            db = client[db_name]

            # Create a simple seed document in a collection called `seed_collection`.
            coll = db.get_collection('seed_collection')

            existing = coll.count_documents({})
            if existing > 0:
                self.stdout.write(self.style.WARNING(f'seed_collection already has {existing} document(s). Skipping insert.'))
            else:
                sample = {
                    'name': 'Artvinci Seed Document',
                    'description': 'This document was created by the seed_db management command.',
                    'created_by': 'seed_db',
                }
                coll.insert_one(sample)
                self.stdout.write(self.style.SUCCESS('Inserted seed document into seed_collection'))

            # Optionally create an index for faster lookups (example)
            try:
                coll.create_index('name', unique=False)
                self.stdout.write(self.style.SUCCESS('Ensured index on seed_collection.name'))
            except Exception:
                pass

            client.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR('Failed to seed database: %s' % str(e)))
