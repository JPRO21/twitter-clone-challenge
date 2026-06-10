from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import Tweet

CREATE_URL = "/tweets/create/"
TIMELINE_URL = "/timeline/"


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


# ---------------------------------------------------------------------------
# Tweet creation view
# ---------------------------------------------------------------------------

class TweetCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123!",
        )
        self.other = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="alice", password="StrongPass123!")

    # -- GET ------------------------------------------------------------------

    def test_create_page_loads(self):
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 200)

    def test_create_page_contains_form(self):
        response = self.client.get(CREATE_URL)
        self.assertContains(response, "<form")
        self.assertContains(response, "name=\"body\"")

    def test_create_page_extends_base(self):
        response = self.client.get(CREATE_URL)
        self.assertContains(response, "Twitter Clone")

    # -- POST: success --------------------------------------------------------

    def test_authenticated_user_can_create_tweet(self):
        response = self.client.post(CREATE_URL, {"body": "Hello, world!"})
        self.assertEqual(Tweet.objects.count(), 1)

    def test_created_tweet_belongs_to_request_user(self):
        self.client.post(CREATE_URL, {"body": "My tweet"})
        tweet = Tweet.objects.get()
        self.assertEqual(tweet.author, self.user)

    def test_successful_creation_redirects_to_profile(self):
        response = self.client.post(CREATE_URL, {"body": "Hello!"})
        self.assertRedirects(
            response,
            reverse("profile", kwargs={"username": "alice"}),
        )

    def test_tweet_body_saved_correctly(self):
        self.client.post(CREATE_URL, {"body": "Exact body text"})
        self.assertEqual(Tweet.objects.get().body, "Exact body text")

    # -- POST: author spoofing ------------------------------------------------

    def test_author_cannot_be_spoofed_via_post(self):
        self.client.post(CREATE_URL, {
            "body": "Spoofed tweet",
            "author": self.other.pk,
        })
        tweet = Tweet.objects.get(body="Spoofed tweet")
        self.assertEqual(tweet.author, self.user)

    # -- POST: validation -----------------------------------------------------

    def test_empty_body_rejected(self):
        response = self.client.post(CREATE_URL, {"body": ""})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tweet.objects.count(), 0)

    def test_body_at_280_characters_accepted(self):
        self.client.post(CREATE_URL, {"body": "x" * 280})
        self.assertEqual(Tweet.objects.count(), 1)

    def test_body_over_280_characters_rejected(self):
        response = self.client.post(CREATE_URL, {"body": "x" * 281})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Tweet.objects.count(), 0)

    def test_validation_errors_shown_in_template(self):
        response = self.client.post(CREATE_URL, {"body": ""})
        self.assertContains(response, "This field is required")

    # -- Anonymous access -----------------------------------------------------

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(CREATE_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_anonymous_redirect_includes_next_parameter(self):
        self.client.logout()
        response = self.client.get(CREATE_URL)
        self.assertIn("next=", response["Location"])

    def test_anonymous_next_points_to_create_url(self):
        self.client.logout()
        response = self.client.get(CREATE_URL)
        self.assertIn("/tweets/create/", response["Location"])

    def test_anonymous_post_does_not_create_tweet(self):
        self.client.logout()
        self.client.post(CREATE_URL, {"body": "Should not save"})
        self.assertEqual(Tweet.objects.count(), 0)


# ---------------------------------------------------------------------------
# Timeline view
# ---------------------------------------------------------------------------

class TimelineViewTest(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice", email="alice@example.com", password="StrongPass123!"
        )
        self.bob = User.objects.create_user(
            username="bob", email="bob@example.com", password="StrongPass123!"
        )
        self.client.login(username="alice", password="StrongPass123!")

    # -- Access ---------------------------------------------------------------

    def test_timeline_loads_for_authenticated_user(self):
        response = self.client.get(TIMELINE_URL)
        self.assertEqual(response.status_code, 200)

    def test_timeline_also_accessible_at_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(TIMELINE_URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login/", response["Location"])

    def test_anonymous_redirect_includes_next(self):
        self.client.logout()
        response = self.client.get(TIMELINE_URL)
        self.assertIn("next=", response["Location"])

    # -- Content --------------------------------------------------------------

    def test_tweets_appear_on_timeline(self):
        Tweet.objects.create(author=self.alice, body="Hello from Alice")
        response = self.client.get(TIMELINE_URL)
        self.assertContains(response, "Hello from Alice")

    def test_tweets_from_other_users_appear(self):
        Tweet.objects.create(author=self.bob, body="Hello from Bob")
        response = self.client.get(TIMELINE_URL)
        self.assertContains(response, "Hello from Bob")

    def test_author_display_name_shown(self):
        self.alice.display_name = "Alice Smith"
        self.alice.save()
        Tweet.objects.create(author=self.alice, body="Name test")
        response = self.client.get(TIMELINE_URL)
        self.assertContains(response, "Alice Smith")

    def test_author_username_shown(self):
        Tweet.objects.create(author=self.alice, body="Username test")
        response = self.client.get(TIMELINE_URL)
        self.assertContains(response, "@alice")

    def test_tweet_body_shown(self):
        Tweet.objects.create(author=self.alice, body="Specific body content")
        response = self.client.get(TIMELINE_URL)
        self.assertContains(response, "Specific body content")

    def test_empty_timeline_shows_empty_state(self):
        response = self.client.get(TIMELINE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tweets yet")

    # -- Ordering -------------------------------------------------------------

    def test_newest_tweets_appear_first(self):
        t1 = Tweet.objects.create(author=self.alice, body="Older tweet")
        t2 = Tweet.objects.create(author=self.alice, body="Newer tweet")
        response = self.client.get(TIMELINE_URL)
        content = response.content.decode()
        self.assertLess(content.index("Newer tweet"), content.index("Older tweet"))

    # -- Cap at 20 ------------------------------------------------------------

    def test_timeline_capped_at_20_tweets(self):
        for i in range(25):
            Tweet.objects.create(author=self.alice, body=f"Tweet {i:02d}")
        response = self.client.get(TIMELINE_URL)
        # The view slices to 20; check context directly
        self.assertEqual(len(response.context["tweets"]), 20)

    def test_older_tweets_beyond_20_not_shown(self):
        for i in range(25):
            Tweet.objects.create(author=self.alice, body=f"Tweet {i:02d}")
        response = self.client.get(TIMELINE_URL)
        # Tweet 00 is the oldest and should not appear (only newest 20 shown)
        self.assertNotContains(response, "Tweet 00")

    # -- N+1 / query count ----------------------------------------------------

    def test_query_count_does_not_grow_with_more_authors(self):
        """select_related ensures author data is fetched in the same query."""
        for i in range(10):
            u = User.objects.create_user(
                username=f"u{i}", email=f"u{i}@ex.com", password="p"
            )
            Tweet.objects.create(author=u, body=f"Tweet by u{i}")

        # Measured: session(1) + user(1) + tweets-with-author-join(1) = 3.
        # Flat regardless of author count — proves select_related works.
        with self.assertNumQueries(3):
            response = self.client.get(TIMELINE_URL)
        self.assertEqual(response.status_code, 200)
