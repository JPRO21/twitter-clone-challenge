from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from accounts.models import User

fake = Faker()

SEED_DOMAIN = "@seed.example.com"
DEMO_EMAIL = "demo@seed.example.com"
DEMO_PASSWORD = "password123"


def _unique_username(base, taken):
    if base not in taken:
        return base
    n = 1
    while f"{base}{n}" in taken:
        n += 1
    return f"{base}{n}"


class Command(BaseCommand):
    help = "Seed the database with demo users. Safe to run multiple times."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Deleting existing seed data...")
        deleted, _ = User.objects.filter(email__endswith=SEED_DOMAIN).delete()
        self.stdout.write(f"  Removed {deleted} existing seed users.")

        self.stdout.write("Creating seed users...")
        taken = set()

        # Demo account — always created with a predictable credential
        User.objects.create_user(
            username="demo",
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            display_name="Demo User",
            bio="The demo account. Use this to log in after seeding.",
        )
        taken.add("demo")

        # 9 random users
        for _ in range(9):
            username = _unique_username(fake.user_name(), taken)
            taken.add(username)
            User.objects.create_user(
                username=username,
                email=f"{username}{SEED_DOMAIN}",
                password=DEMO_PASSWORD,
                display_name=fake.name(),
                bio=fake.sentence(),
            )

        count = User.objects.filter(email__endswith=SEED_DOMAIN).count()
        self.stdout.write(self.style.SUCCESS(
            f"Done. {count} seed users created. "
            f"Demo credentials: {DEMO_EMAIL} / {DEMO_PASSWORD}"
        ))
