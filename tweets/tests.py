from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from accounts.models import User
from .models import Tweet


class TweetModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass",
        )

    def test_create_tweet(self):
        tweet = Tweet.objects.create(author=self.user, body="Hello, world!")
        self.assertEqual(tweet.body, "Hello, world!")
        self.assertEqual(tweet.author, self.user)
        self.assertIsNotNone(tweet.pk)

    def test_author_required(self):
        with self.assertRaises(IntegrityError):
            Tweet.objects.create(body="No author here")

    def test_body_max_length_is_280(self):
        tweet = Tweet(author=self.user, body="x" * 280)
        tweet.full_clean()  # must not raise

    def test_body_over_280_fails_validation(self):
        tweet = Tweet(author=self.user, body="x" * 281)
        with self.assertRaises(ValidationError):
            tweet.full_clean()

    def test_empty_body_fails_validation(self):
        tweet = Tweet(author=self.user, body="")
        with self.assertRaises(ValidationError):
            tweet.full_clean()

    def test_created_at_auto_populated(self):
        tweet = Tweet.objects.create(author=self.user, body="Timestamp test")
        self.assertIsNotNone(tweet.created_at)

    def test_updated_at_auto_populated(self):
        tweet = Tweet.objects.create(author=self.user, body="Timestamp test")
        self.assertIsNotNone(tweet.updated_at)

    def test_updated_at_changes_on_save(self):
        tweet = Tweet.objects.create(author=self.user, body="Original")
        before = tweet.updated_at
        tweet.body = "Modified"
        tweet.save()
        tweet.refresh_from_db()
        self.assertGreaterEqual(tweet.updated_at, before)

    def test_cascade_delete_removes_tweets_when_author_deleted(self):
        Tweet.objects.create(author=self.user, body="Will be gone")
        Tweet.objects.create(author=self.user, body="Also gone")
        self.assertEqual(Tweet.objects.count(), 2)
        self.user.delete()
        self.assertEqual(Tweet.objects.count(), 0)

    def test_cascade_does_not_affect_other_authors_tweets(self):
        other = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass",
        )
        Tweet.objects.create(author=self.user, body="User 1 tweet")
        Tweet.objects.create(author=other, body="User 2 tweet")
        self.user.delete()
        self.assertEqual(Tweet.objects.count(), 1)
        self.assertEqual(Tweet.objects.first().author, other)

    def test_default_ordering_newest_first(self):
        t1 = Tweet.objects.create(author=self.user, body="First")
        t2 = Tweet.objects.create(author=self.user, body="Second")
        tweets = list(Tweet.objects.all())
        self.assertEqual(tweets[0], t2)
        self.assertEqual(tweets[1], t1)

    def test_index_exists(self):
        index_names = [idx.name for idx in Tweet._meta.indexes]
        self.assertIn("tweet_author_created_idx", index_names)

    def test_index_covers_author_and_created_at(self):
        idx = next(i for i in Tweet._meta.indexes if i.name == "tweet_author_created_idx")
        self.assertEqual(list(idx.fields), ["author", "created_at"])

    def test_str_contains_username_and_body(self):
        tweet = Tweet.objects.create(author=self.user, body="Hello!")
        self.assertIn("testuser", str(tweet))
        self.assertIn("Hello!", str(tweet))

    def test_related_name_tweets_on_user(self):
        Tweet.objects.create(author=self.user, body="Tweet A")
        Tweet.objects.create(author=self.user, body="Tweet B")
        self.assertEqual(self.user.tweets.count(), 2)
