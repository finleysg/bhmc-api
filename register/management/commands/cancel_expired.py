from django.core.management.base import BaseCommand
from register.models import RegistrationGroup


class Command(BaseCommand):
    help = 'Find and clear pending registrations that have expired'

    def handle(self, *args, **options):
        count = RegistrationGroup.objects.clean_up_expired()
        self.stdout.write(self.style.SUCCESS('Cleared %s expired groups' % count))
