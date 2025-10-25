from django.core.management.base import BaseCommand
from forum.models import ForumCategory

class Command(BaseCommand):
    help = 'Cleanup forum categories: remove test category (--remove-test) and optionally seed standard categories (--seed).'

    def add_arguments(self, parser):
        parser.add_argument('--remove-test', action='store_true', help='Remove categories named "test" (case-insensitive).')
        parser.add_argument('--seed', action='store_true', help='Create seed categories for all CategoryType values if missing.')
        parser.add_argument('--pattern', type=str, help='Remove categories whose name contains this substring (case-insensitive).')
        parser.add_argument('--force', action='store_true', help='Actually perform deletions for --pattern (safety flag).')

    def handle(self, *args, **options):
        removed_count = 0
        if options.get('remove_test'):
            # Remove any category whose name contains 'test' (case-insensitive)
            qs = ForumCategory.objects(name__icontains='test')
            removed_count = qs.count()
            for c in qs:
                self.stdout.write(self.style.WARNING(f'Deleting category: {c.name} ({str(c.id)})'))
                c.delete()
            self.stdout.write(self.style.SUCCESS(f'Removed {removed_count} test-like category(ies).'))

        # Support removing by arbitrary substring pattern; require --force to actually delete for safety
        pattern = options.get('pattern')
        if pattern:
            qs = ForumCategory.objects(name__icontains=pattern)
            count = qs.count()
            if count == 0:
                self.stdout.write(self.style.NOTICE(f'No categories match pattern "{pattern}".'))
            else:
                self.stdout.write(self.style.WARNING(f'Found {count} categories matching "{pattern}":'))
                for c in qs:
                    self.stdout.write(f'  - {c.name} ({str(c.id)})')
                if not options.get('force'):
                    self.stdout.write(self.style.NOTICE('Run again with --force to actually delete these categories.'))
                else:
                    deleted = 0
                    for c in qs:
                        self.stdout.write(self.style.WARNING(f'Deleting category: {c.name} ({str(c.id)})'))
                        c.delete()
                        deleted += 1
                    self.stdout.write(self.style.SUCCESS(f'Deleted {deleted} categories matching "{pattern}".'))

        if options.get('seed'):
            # Curated categories to seed into the forum. These are friendly French labels
            # mapped to the CategoryType values. Existing categories (case-insensitive by name)
            # will not be duplicated.
            CATEGORIES_TO_SEED = [
                { 'name': 'Annonces', 'description': 'Communiqués officiels et nouvelles', 'type': 'announcements' },
                { 'name': 'Discussions générales', 'description': 'Échanges ouverts sur l’art et la communauté', 'type': 'general' },
                { 'name': 'Aide & conseils', 'description': "Questions techniques et conseils d'autres artistes", 'type': 'help' },
                { 'name': 'Tutoriels & techniques', 'description': 'Guides pas-à-pas et techniques de création', 'type': 'tutorials' },
                { 'name': 'Galerie / Showcases', 'description': "Partagez vos œuvres et votre processus créatif", 'type': 'showcase' },
                { 'name': 'Événements', 'description': 'Ateliers, expositions et événements locaux', 'type': 'events' },
                { 'name': 'Hors-sujet', 'description': 'Discussions détendues sans rapport direct avec l’art', 'type': 'offtopic' },
                { 'name': 'Retours & suggestions', 'description': 'Feedback sur le site, idées et améliorations', 'type': 'feedback' },
                { 'name': 'Offres & commandes', 'description': 'Annonces d’emploi, commissions et opportunités', 'type': 'jobs' },
                { 'name': 'Modération', 'description': 'Signalements et questions liées aux règles', 'type': 'moderation' },
            ]

            created = 0
            for item in CATEGORIES_TO_SEED:
                name = item.get('name')
                desc = item.get('description', '')
                ctype = item.get('type')
                existing = ForumCategory.objects(name__iexact=name).first()
                if existing:
                    self.stdout.write(self.style.NOTICE(f'Category exists, skipping: {name}'))
                    continue
                try:
                    c = ForumCategory(name=name, description=desc, category_type=ctype)
                    c.save()
                    created += 1
                    self.stdout.write(self.style.SUCCESS(f'Created category: {name} ({ctype})'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Failed to create {name}: {e}'))

            self.stdout.write(self.style.SUCCESS(f'Seed complete, created {created} categories.'))

        if not options.get('remove_test') and not options.get('seed'):
            self.stdout.write(self.style.NOTICE('No action taken. Use --remove-test and/or --seed.'))
