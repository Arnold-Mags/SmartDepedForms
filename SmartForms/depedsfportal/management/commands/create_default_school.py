from django.core.management.base import BaseCommand
from depedsfportal.models import School

class Command(BaseCommand):
    help = 'Creates a default school if none exists'

    def handle(self, *args, **options):
        if not School.objects.exists():
            School.objects.create(
                name='Default School',
                region='Default Region'
            )
            self.stdout.write(self.style.SUCCESS('Default school created'))
        else:
            self.stdout.write(self.style.NOTICE('School already exists'))
