from django.core.management import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = 'Initialize DB data'

    def handle(self, *args, **options):
        self.stdout.write("Start user setup...")
        if len(User.objects.all()) == 0:
            user = User(
                username="admin",
                first_name="Super",
                last_name="Administrator",
                email="",
                is_staff=True,
                is_active=True,
                is_superuser=True,
            )
            user.set_password("admin1234!")
            user.save()

        self.stdout.write("Finish user setup")
