# AI Engineering Workflow Log

Claude (Anthropic, claude-sonnet-4-6) was used as an engineering copilot throughout this project. Each entry below covers one feature area: what AI generated, what required human modification, and what the review process caught.

---

## 1. Authentication

**Feature:** Register, login (email or username), logout, `@login_required` protection, `EmailOrUsernameBackend`, session management.

**AI assistance used:**
- Generated `RegisterForm`, `LoginForm`, `ProfileEditForm` with field definitions and clean methods.
- Scaffolded `register`, `login_view`, `logout_view`, `profile_edit` views.
- Wrote `EmailOrUsernameBackend` with `authenticate()` and `get_user()` methods.
- Generated initial `AnonymousAccessTest` suite verifying 302 + `?next=` redirects.

**Human modifications:**
- Required exact `LOGIN_URL = "/login/"` and `url_has_allowed_host_and_scheme` safe-redirect guard — AI initial draft used a bare `redirect(next_url)` that could be manipulated.
- Verified `display_name = username` default is applied on save, not just in the form.

**Review findings:**
- AI correctly used `authenticate(request, ...)` but initially omitted the `request` argument, which is required for some backends. Fixed before commit.
- Safe redirect validation was absent in the first draft — open redirect vulnerability caught in review.

---

## 2. Tweets + Timeline

**Feature:** Tweet model, 280-character limit, tweet creation, timeline with `select_related`, `Count` + `Exists` annotations, offset pagination.

**AI assistance used:**
- Generated `Tweet` model with `author`, `body`, `created_at`, `updated_at` and the composite index `tweet_author_created_idx`.
- Wrote `TweetForm` with `max_length=280` validation.
- Implemented `timeline` view with `select_related("author")`, `Count("likes")`, `Exists(...)` annotations, and `Paginator`.
- Generated `assertNumQueries` test framework and measured baseline at 3 queries, then updated to 4 after pagination was added.

**Human modifications:**
- Required `InvalidPage` (not `PageNotAnInteger` + `EmptyPage` separately) as the catch-all exception class — simpler and catches both.
- Confirmed `Count` + `Exists` compile into a single SQL statement (not two), so query count stayed at 4 not 5.
- Frozen query count updated from 3 → 4 with explanatory comment when `Paginator` was added.

**Review findings:**
- AI initially used `Tweet.objects.filter(...)` without `select_related`, causing N+1. Caught by `assertNumQueries` test before it could be committed.
- Pagination fallback to page 1 on `InvalidPage` was not in the first draft — added after reviewing the spec's pagination requirement.

---

## 3. Social: Follow + Like

**Feature:** Follow model with self-follow `CheckConstraint`, `UniqueConstraint`, idempotent follow/unfollow; Like model with `UniqueConstraint`, idempotent like/unlike; profile follow counts; search with `Q` + `Exists` annotation.

**AI assistance used:**
- Generated `Follow` model with both constraints and composite index.
- Wrote `follow_user`, `unfollow_user` views using `get_or_create` / `filter().delete()`.
- Generated `Like` model, `like_tweet`, `unlike_tweet` views.
- Implemented `search_users` with `Q(username__icontains=...) | Q(display_name__icontains=...)` and `Exists(following_qs)` annotation per result row.

**Human modifications:**
- Required exact related names `following_relationships` and `follower_relationships` (not the default `following`/`followers`) — enforced by user review of the generated model.
- Required exact constraint names `unique_follow_relationship` and `prevent_self_follow` matching the spec.
- `CheckConstraint` parameter name: Django 6.0.6 renamed `check=` to `condition=`. AI used the old name; caught by running `migrate` and reading the traceback.
- Search template loop variable renamed from `user` to `result` to prevent shadowing Django's `{{ user }}` context variable.

**Review findings:**
- `CheckConstraint(check=...)` TypeError was the most significant error — not caught by static analysis, only by running migrations. Documented in the error log.
- Related name test `alice.following.count()` failed after rename to `following_relationships` — found by running the test suite immediately after model changes.

---

## 4. Testing

**Feature:** 198 tests across `accounts/tests.py` and `tweets/tests.py`; 99% backend coverage.

**AI assistance used:**
- Generated full test classes for all models, views, and integration flows.
- Wrote `assertNumQueries(4)` performance test with breakdown comment.
- Generated `TimelinePaginationTest` covering first-page, exact-20, N+1 regression, and invalid-page fallback.
- Wrote `SearchViewTest` covering username search, display-name search, case-insensitivity, current-user exclusion.

**Human modifications:**
- `test_case_insensitive_display_name_search` initially searched `"alice smith"` and asserted `"bob"` in results — but alice was the logged-in user (excluded from search). Fixed by searching `"BOB JONES"` (uppercase of bob's display_name).
- `assertNumQueries(3)` → `assertNumQueries(4)` when `Paginator` added a `COUNT(*)` query. Investigated before updating the frozen number.
- Parallel `pytest` + `pytest --cov` runs caused a test database race condition. Resolved by running them sequentially.

**Review findings:**
- Test database isolation: `pytest-django` resets the DB between tests, but parallel Docker `pytest` runs share the same `test_twitter_clone` database — they must run sequentially.
- The `assertNumQueries` discipline caught two N+1 regressions before merge.

---

## 5. Docker + Documentation

**Feature:** `Dockerfile`, `docker-compose.yml`, `Makefile`, seed command with Faker, `README.md`, `DECISIONS.md`, `.env.example`.

**AI assistance used:**
- Generated `Dockerfile` with `psycopg2` system dependencies (`libpq-dev gcc`).
- Wrote `docker-compose.yml` with `web` + `db` services, volume, and health check.
- Generated `Makefile` with all targets from the spec.
- Wrote full `seed.py` with `@transaction.atomic`, Faker, idempotent delete-by-domain, 10 users, 60 tweets, 32 follows, 63 likes.
- Drafted all sections of `README.md` and `DECISIONS.md`.

**Human modifications:**
- Seed command initially had no DB-existence guard — `accounts_follow` table missing caused a crash on first run (before migrations). Fixed by running `manage.py migrate` before `seed`.
- `_unique_username` updated to also query the DB for conflicts with existing non-seed usernames, not just the in-memory `taken` set.
- Idempotency validated by running seed three consecutive times; all three succeeded cleanly.

**Review findings:**
- CASCADE delete on `User` propagates through `Tweet`, `Follow`, and `Like` — confirmed that second seed run removed 165 objects (not just 10 users).
- Documentation review caught that `pytest --cov=.` (not `pytest --cov`) is required for the `term-missing` report to include all modules.
