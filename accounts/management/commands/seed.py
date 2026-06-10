import random

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from accounts.models import Follow, User
from tweets.models import Like, Tweet

fake = Faker()

SEED_DOMAIN = "@seed.example.com"
DEMO_EMAIL = "demo@seed.example.com"
DEMO_PASSWORD = "password123"

NUM_EXTRA_USERS = 9       # + 1 demo = 10 total (spec: ≥10)
TWEETS_PER_USER = 6       # 10 × 6 = 60 tweets (spec: ≥50)


def _unique_username(base, taken):
    """Return a username that is not in `taken` and not already in the DB."""
    candidate = base[:30]
    if candidate not in taken and not User.objects.filter(username=candidate).exists():
        return candidate
    n = 1
    while (
        f"{candidate}{n}" in taken
        or User.objects.filter(username=f"{candidate}{n}").exists()
    ):
        n += 1
    return f"{candidate}{n}"


class Command(BaseCommand):
    help = "Seed the database with demo data. Idempotent — safe to run multiple times."

    @transaction.atomic
    def handle(self, *args, **options):
        w = self.stdout.write

        # ------------------------------------------------------------------ #
        # 1. Wipe previous seed data                                          #
        # CASCADE propagates: tweets, follows, and likes are removed too.    #
        # ------------------------------------------------------------------ #
        w("Deleting existing seed data…")
        deleted, breakdown = User.objects.filter(email__endswith=SEED_DOMAIN).delete()
        w(f"  Removed {deleted} objects ({breakdown}).")

        # ------------------------------------------------------------------ #
        # 2. Users                                                            #
        # ------------------------------------------------------------------ #
        w("Creating seed users…")
        taken: set[str] = set()

        demo = User.objects.create_user(
            username="demo",
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            display_name="Demo User",
            bio="The demo account. Log in with demo@seed.example.com / password123.",
        )
        taken.add("demo")

        others: list[User] = []
        for _ in range(NUM_EXTRA_USERS):
            username = _unique_username(fake.user_name(), taken)
            taken.add(username)
            user = User.objects.create_user(
                username=username,
                email=f"{username}{SEED_DOMAIN}",
                password=DEMO_PASSWORD,
                display_name=fake.name(),
                bio=fake.sentence(),
            )
            others.append(user)

        all_users = [demo] + others
        w(f"  Created {len(all_users)} users.")

        # ------------------------------------------------------------------ #
        # 3. Tweets (≥50)                                                     #
        # ------------------------------------------------------------------ #
        w("Creating tweets…")
        all_tweets: list[Tweet] = []
        for user in all_users:
            for _ in range(TWEETS_PER_USER):
                body = fake.sentence(nb_words=random.randint(5, 18))
                tweet = Tweet.objects.create(author=user, body=body)
                all_tweets.append(tweet)
        w(f"  Created {len(all_tweets)} tweets.")

        # ------------------------------------------------------------------ #
        # 4. Follow relationships                                             #
        # Demo follows everyone → its timeline is immediately populated.     #
        # ------------------------------------------------------------------ #
        w("Creating follow relationships…")
        follow_pairs: list[tuple] = []

        # Demo follows all others
        for user in others:
            Follow.objects.create(follower=demo, following=user)
            follow_pairs.append((demo.pk, user.pk))

        # Roughly half of others follow demo back
        for user in others[: len(others) // 2 + 1]:
            Follow.objects.create(follower=user, following=demo)
            follow_pairs.append((user.pk, demo.pk))

        # Ring: each user in `others` follows the next two (wrap-around)
        seen_follows: set[tuple] = set(follow_pairs)
        for i, user in enumerate(others):
            for offset in (1, 2):
                target = others[(i + offset) % len(others)]
                pair = (user.pk, target.pk)
                if pair not in seen_follows:
                    Follow.objects.create(follower=user, following=target)
                    seen_follows.add(pair)

        w(f"  Created {len(seen_follows)} follow relationships.")

        # ------------------------------------------------------------------ #
        # 5. Likes                                                            #
        # ------------------------------------------------------------------ #
        w("Creating likes…")
        seen_likes: set[tuple] = set()

        def _like(user: User, tweet: Tweet) -> None:
            pair = (user.pk, tweet.pk)
            if pair not in seen_likes:
                Like.objects.create(user=user, tweet=tweet)
                seen_likes.add(pair)

        # Demo likes the first 3 tweets of every other user
        for user in others:
            for tweet in Tweet.objects.filter(author=user).order_by("created_at")[:3]:
                _like(demo, tweet)

        # Every other user likes demo's first 2 tweets
        demo_tweets = list(Tweet.objects.filter(author=demo).order_by("created_at")[:2])
        for user in others:
            for tweet in demo_tweets:
                _like(user, tweet)

        # Cross-likes: each user in `others` likes 2 tweets from the next user
        for i, user in enumerate(others):
            next_user = others[(i + 1) % len(others)]
            for tweet in Tweet.objects.filter(author=next_user).order_by("created_at")[:2]:
                _like(user, tweet)

        w(f"  Created {len(seen_likes)} likes.")

        # ------------------------------------------------------------------ #
        # 6. Summary                                                          #
        # ------------------------------------------------------------------ #
        self.stdout.write(self.style.SUCCESS(
            "\nSeed complete!\n"
            f"  Users:   {User.objects.filter(email__endswith=SEED_DOMAIN).count()}\n"
            f"  Tweets:  {len(all_tweets)}\n"
            f"  Follows: {len(seen_follows)}\n"
            f"  Likes:   {len(seen_likes)}\n"
            f"\nDemo login → email: {DEMO_EMAIL}  password: {DEMO_PASSWORD}"
        ))
