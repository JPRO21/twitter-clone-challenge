from django.test import TestCase
from django.urls import reverse

from .models import User


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class UserModelTest(TestCase):
    def test_unique_email_enforced(self):
        User.objects.create_user(username="alice", email="alice@example.com", password="pass")
        with self.assertRaises(Exception):
            User.objects.create_user(username="alice2", email="alice@example.com", password="pass")

    def test_unique_username_enforced(self):
        User.objects.create_user(username="alice", email="alice@example.com", password="pass")
        with self.assertRaises(Exception):
            User.objects.create_user(username="alice", email="other@example.com", password="pass")

    def test_display_name_defaults_to_username_via_registration(self):
        self.client.post(reverse("register"), {
            "username": "alice",
            "email": "alice@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        user = User.objects.get(username="alice")
        self.assertEqual(user.display_name, "alice")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterViewTest(TestCase):
    URL = "/register/"

    def test_register_page_loads(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    def test_successful_registration_creates_user(self):
        response = self.client.post(self.URL, {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertRedirects(response, reverse("login"))
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_sets_display_name_to_username(self):
        self.client.post(self.URL, {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertEqual(User.objects.get(username="newuser").display_name, "newuser")

    def test_duplicate_email_rejected(self):
        User.objects.create_user(username="existing", email="taken@example.com", password="pass")
        response = self.client.post(self.URL, {
            "username": "another",
            "email": "taken@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="another").exists())

    def test_duplicate_username_rejected(self):
        User.objects.create_user(username="existing", email="a@example.com", password="pass")
        response = self.client.post(self.URL, {
            "username": "existing",
            "email": "new@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username="existing").count(), 1)

    def test_password_mismatch_rejected(self):
        response = self.client.post(self.URL, {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password_confirm": "Different123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_password_is_hashed_not_stored_plaintext(self):
        self.client.post(self.URL, {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        user = User.objects.get(username="newuser")
        self.assertNotEqual(user.password, "StrongPass123!")
        self.assertTrue(user.password.startswith("pbkdf2_") or "argon2" in user.password or "bcrypt" in user.password)

    def test_authenticated_user_redirected_away_from_register(self):
        User.objects.create_user(username="u", email="u@example.com", password="pass")
        self.client.login(username="u", password="pass")
        response = self.client.get(self.URL)
        self.assertRedirects(response, reverse("home"))


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

class LoginViewTest(TestCase):
    URL = "/login/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="StrongPass123!",
        )

    def test_login_page_loads(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    def test_login_with_username_succeeds(self):
        response = self.client.post(self.URL, {
            "username": "testuser",
            "password": "StrongPass123!",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_with_email_succeeds(self):
        response = self.client.post(self.URL, {
            "username": "test@example.com",
            "password": "StrongPass123!",
        })
        self.assertRedirects(response, reverse("home"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_wrong_password_rejected(self):
        response = self.client.post(self.URL, {
            "username": "testuser",
            "password": "wrongpassword",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_nonexistent_user_rejected(self):
        response = self.client.post(self.URL, {
            "username": "nobody",
            "password": "StrongPass123!",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_respects_next_parameter(self):
        response = self.client.post(
            self.URL + "?next=/some-path/",
            {"username": "testuser", "password": "StrongPass123!", "next": "/some-path/"},
        )
        self.assertRedirects(response, "/some-path/", fetch_redirect_response=False)

    def test_authenticated_user_redirected_away_from_login(self):
        self.client.login(username="testuser", password="StrongPass123!")
        response = self.client.get(self.URL)
        self.assertRedirects(response, reverse("home"))


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class LogoutViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="testuser", password="StrongPass123!")

    def test_logout_destroys_session(self):
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_redirects_to_login(self):
        response = self.client.post(reverse("logout"))
        self.assertRedirects(response, reverse("login"))

    def test_logout_get_still_redirects(self):
        # GET to logout should not error; spec uses POST but GET is a safe fallback
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)


# ---------------------------------------------------------------------------
# Anonymous access / next parameter
# ---------------------------------------------------------------------------

class AnonymousAccessTest(TestCase):
    def test_home_redirects_anonymous_to_login(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_redirect_includes_next_parameter(self):
        response = self.client.get(reverse("home"))
        self.assertIn("next=", response["Location"])

    def test_next_points_to_requested_path(self):
        response = self.client.get(reverse("home"))
        self.assertIn("next=/", response["Location"])


# ---------------------------------------------------------------------------
# End-to-end authentication flow
# ---------------------------------------------------------------------------

class AuthE2ETest(TestCase):
    def test_register_login_access_logout_flow(self):
        # 1. Register
        resp = self.client.post(reverse("register"), {
            "username": "e2euser",
            "email": "e2e@example.com",
            "password": "StrongPass123!",
            "password_confirm": "StrongPass123!",
        })
        self.assertRedirects(resp, reverse("login"))
        self.assertTrue(User.objects.filter(username="e2euser").exists())

        # 2. Login
        resp = self.client.post(reverse("login"), {
            "username": "e2euser",
            "password": "StrongPass123!",
        })
        self.assertRedirects(resp, reverse("home"))

        # 3. Access protected page — 200
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 200)

        # 4. Logout
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)

        # 5. Same protected page now redirects to login
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse("login"), resp["Location"])


# ---------------------------------------------------------------------------
# Profile view
# ---------------------------------------------------------------------------

class ProfileViewTest(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123!",
            display_name="Alice Smith",
            bio="Hello, I'm Alice.",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123!",
            display_name="Bob Jones",
        )
        self.client.login(username="alice", password="StrongPass123!")

    def test_profile_page_loads(self):
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(response.status_code, 200)

    def test_profile_shows_username(self):
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertContains(response, "alice")

    def test_profile_shows_display_name(self):
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertContains(response, "Alice Smith")

    def test_profile_shows_bio(self):
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertContains(response, "Hello, I&#x27;m Alice.")

    def test_profile_shows_date_joined(self):
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Joined")

    def test_profile_shows_edit_button_for_own_profile(self):
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertContains(response, "Edit profile")

    def test_profile_hides_edit_button_for_other_profile(self):
        response = self.client.get(reverse("profile", kwargs={"username": "bob"}))
        self.assertNotContains(response, "Edit profile")

    def test_authenticated_user_can_view_other_profile(self):
        response = self.client.get(reverse("profile", kwargs={"username": "bob"}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bob Jones")

    def test_nonexistent_user_returns_404(self):
        response = self.client.get(reverse("profile", kwargs={"username": "nobody"}))
        self.assertEqual(response.status_code, 404)

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_anonymous_redirect_includes_next(self):
        self.client.logout()
        response = self.client.get(reverse("profile", kwargs={"username": "alice"}))
        self.assertIn("next=", response["Location"])


# ---------------------------------------------------------------------------
# Profile edit
# ---------------------------------------------------------------------------

class ProfileEditViewTest(TestCase):
    URL = "/settings/profile/"

    def setUp(self):
        self.alice = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="StrongPass123!",
            display_name="Alice",
            bio="Old bio",
        )
        self.bob = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="StrongPass123!",
        )
        self.client.login(username="alice", password="StrongPass123!")

    def test_edit_page_loads(self):
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "<form")

    def test_edit_page_shows_current_display_name(self):
        response = self.client.get(self.URL)
        self.assertContains(response, "Alice")

    def test_edit_page_shows_current_bio(self):
        response = self.client.get(self.URL)
        self.assertContains(response, "Old bio")

    def test_edit_updates_display_name(self):
        self.client.post(self.URL, {"display_name": "Alice Updated", "bio": "Old bio"})
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.display_name, "Alice Updated")

    def test_edit_updates_bio(self):
        self.client.post(self.URL, {"display_name": "Alice", "bio": "Brand new bio"})
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.bio, "Brand new bio")

    def test_edit_redirects_to_own_profile_on_success(self):
        response = self.client.post(self.URL, {"display_name": "Alice", "bio": "Bio"})
        self.assertRedirects(response, reverse("profile", kwargs={"username": "alice"}))

    def test_edit_does_not_affect_other_users(self):
        self.client.post(self.URL, {"display_name": "Alice", "bio": "Updated"})
        self.bob.refresh_from_db()
        self.assertNotEqual(self.bob.bio, "Updated")

    def test_anonymous_user_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response["Location"])

    def test_anonymous_redirect_includes_next(self):
        self.client.logout()
        response = self.client.get(self.URL)
        self.assertIn("next=", response["Location"])

    def test_anonymous_post_does_not_save(self):
        self.client.logout()
        self.client.post(self.URL, {"display_name": "Hacked", "bio": "Hacked"})
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.display_name, "Alice")
