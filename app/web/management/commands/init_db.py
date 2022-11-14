from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Initialize DB data'

    def handle(self, *args, **options):
        self.stdout.write("Start db initialization ...")
        # create user group for permissions
        Group.objects.update_or_create(id=1, defaults={"name": "ccc"})
        self.stdout.write("Finish db initialization")
