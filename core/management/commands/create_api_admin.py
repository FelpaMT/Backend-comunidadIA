from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from core.models import Role, User


class Command(BaseCommand):
    help = "Create an administrator account for the ComunidadIA API."

    def handle(self, *args, **options):
        email = input("Admin email: ").strip().lower()
        name = input("Admin name: ").strip()
        if not email or not name:
            raise CommandError("Name and email are required.")
        if User.objects.filter(email__iexact=email).exists():
            raise CommandError("A ComunidadIA user with this email already exists.")

        password = getpass("Password (at least 12 characters): ")
        confirmation = getpass("Confirm password: ")
        if password != confirmation:
            raise CommandError("The passwords do not match.")

        user = User(name=name, email=email, role=Role.ADMIN, is_verified=True)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from exc

        user.set_password(password)
        user.save()
        self.stdout.write(self.style.SUCCESS(f"API administrator created: {email}"))
