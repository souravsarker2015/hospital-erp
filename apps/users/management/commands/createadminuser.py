import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Creates a platform admin account (is_staff=is_superuser=True, hospital=None) "
        "for /admin/ and /platform/ — not tied to any single hospital. Prompts for "
        "anything not passed as a flag."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Login username")
        parser.add_argument("--email", help="Email address")
        parser.add_argument("--password", help="Password (prompted securely if omitted)")

    def handle(self, *args, **options):
        UserModel = get_user_model()

        username = options["username"] or input("Username: ")
        if not username:
            raise CommandError("Username is required.")
        if UserModel.objects.filter(username=username).exists():
            raise CommandError(f"A user with username '{username}' already exists.")

        email = options["email"]
        if email is None:
            email = input("Email address: ")

        password = options["password"]
        if not password:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password (again): "):
                raise CommandError("Passwords didn't match.")
        if not password:
            raise CommandError("Password is required.")

        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError("\n".join(exc.messages)) from exc

        user = UserModel.objects.create_superuser(username=username, email=email, password=password)

        self.stdout.write(
            self.style.SUCCESS(
                f"Platform admin '{user.username}' created "
                f"(is_staff={user.is_staff}, is_superuser={user.is_superuser}, hospital={user.hospital_id})."
            )
        )
