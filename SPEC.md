# Twitter Clone Challenge — Development Spec v2.0 Final

> This is the frozen specification. No architectural changes after this version.
> Implementation problems are resolved in code, not by modifying this document.
> v2.0: Final clean. Structural fixes only — no new decisions. Ready to code.

---

## Core Principle

This project is optimized for:

1. Deliverability
2. Testability
3. Documentation quality
4. Engineering decision visibility
5. AI-assisted development discipline

The goal is not maximum feature count. The goal is a complete, reliable, well-tested application with a coherent development history.

---

# Success Criteria

The project is successful when:

* All mandatory features work.
* Backend coverage is 85%+.
* Timeline avoids N+1 query regressions.
* Docker Compose runs successfully.
* Seed data generates realistic activity.
* Documentation is complete.
* Git history shows progressive development.
* AI usage is documented honestly.
* Mobile experience is usable.

---

# Scope

## Mandatory Features

Authentication:

* Register
* Login
* Logout
* Session management
* Protected routes

Profile:

* Username
* Display name
* Bio
* Avatar placeholder (initials in CSS div — no model field, no storage)
* Followers count
* Following count

Tweets:

* Create tweet
* Delete own tweet
* 280-character limit
* Timeline
* Pagination

Social:

* Follow
* Unfollow
* Like
* Unlike

Search:

* Search users by username
* Search users by display name

UI:

* Mobile-first responsive design

---

## Planned Bonus

Only one bonus feature is planned.

### Docker Compose

Reason:

* High evaluator value
* Low product complexity
* Improves runbook reliability
* Demonstrates deployment awareness

---

## Explicitly Out of Scope

Explicitly out of scope for this challenge:

* Notifications
* Image uploads
* Reply threads
* Real-time updates
* Direct messages
* Retweets
* Quote tweets
* Hashtags
* Trending topics
* Recommendation systems

---

# Stack

## Backend

Django 5.x

## Frontend

Django Templates + HTMX via CDN

```html
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
```

Reasons:

* Lower complexity, faster implementation
* Reduced JavaScript footprint, server-side rendering simplicity
* No npm build pipeline required

Trade-off: HTMX sacrifices SPA flexibility for delivery speed. CDN delivery avoids build complexity within the 72-hour window. Document in DECISIONS.md.

Progressive enhancement rule: All HTMX interactions must degrade to standard POST form submissions if HTMX fails to load. HTMX enhances the experience — it does not replace the form.

## Styling

Tailwind CSS via CDN

```html
<script src="https://cdn.tailwindcss.com"></script>
```

Reasons:

* Mobile-first workflow, rapid implementation, minimal custom CSS
* No npm build pipeline required

Trade-off: Production would use a compiled build to strip unused classes. CDN is intentional for this challenge. Document in DECISIONS.md.

Note: The app requires internet access for CDN assets in development. If CDN assets are unavailable, functionality remains usable but styling may degrade.

## Database

PostgreSQL

## Testing

* pytest
* pytest-django
* coverage
* Django Test Client for auth E2E flow

## Environment Configuration

* python-decouple or django-environ

## Infrastructure

Docker Compose

---

# Authentication and Access Strategy

## Decision

All application functionality requires authentication.

Homepage redirects to login.

Profile pages, timeline, search, tweet actions, follow actions, and like actions all require login.

## Reason

The challenge evaluates core social features rather than public content discovery. Requiring authentication for all routes simplifies authorization, reduces implementation complexity, decreases testing overhead, and prevents inconsistent behavior between pages.

## Implementation

Use `@login_required` for protected function-based views.

Set `LOGIN_URL` in settings.

## Anonymous Access Tests

Anonymous tests must verify:

* status code is 302
* redirect target is `LOGIN_URL`
* `next` parameter points to the originally requested path

Example:

```
/login/?next=/tweets/create/
```

---

# Environment Configuration

Settings must read all configuration from environment variables from the first commit.

Use `python-decouple` or `django-environ`.

The same `settings.py` must work locally and inside Docker without modification.

## Required Variables

```
SECRET_KEY=your-secret-key-here
DEBUG=True
DATABASE_URL=postgres://postgres:postgres@db:5432/twitter_clone
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CSRF_TRUSTED_ORIGINS=http://localhost:8000
```

## settings.py Configuration

```python
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
DATABASE_URL = config("DATABASE_URL")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost").split(",")

raw_csrf = config("CSRF_TRUSTED_ORIGINS", default="http://localhost:8000")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in raw_csrf.split(",") if o.strip()]
```

`ALLOWED_HOSTS` note: Docker routes requests through internal IPs. `localhost` alone causes `400 Bad Request` when accessed via `127.0.0.1`. Explicit configuration prevents this.

`CSRF_TRUSTED_ORIGINS` note: Required for Docker and proxy deployments where the origin header differs from the expected host.

## .env.example

Must be complete and committed from step 2.

Evaluator setup:

```bash
cp .env.example .env
```

---

# User Model Strategy

## Decision

Use a custom user model from the first commit.

```python
class User(AbstractUser):
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
```

Settings:

```python
AUTH_USER_MODEL = "accounts.User"
```

## Migration Safety Rule

`AUTH_USER_MODEL` must be configured before the first migration.

Do not run:

```bash
python manage.py migrate
```

before the custom user model is defined and `AUTH_USER_MODEL` is set.

## Rules

Do not create a custom `password_hash` field.

Use:

* Django native password field
* Django authentication framework
* Django password hashing

## Display Name Default

Registration collects: email, username, password.

`display_name` defaults to `username` if blank:

```python
if not user.display_name:
    user.display_name = user.username
```

## Avatar Placeholder

Implemented as initials of `display_name` in a styled CSS div.

No model field required.
No file storage required.
No image uploads.

Example (Tailwind):

```html
<div class="w-10 h-10 rounded-full bg-slate-500 flex items-center justify-center text-white font-bold">
  {{ user.display_name|slice:":2"|upper }}
</div>
```

---

# Domain Model

## Tweet

Fields:

* id
* author_id
* body
* created_at
* updated_at

Rules:

* max 280 characters
* hard delete
* owner-only deletion

Index:

```python
models.Index(
    fields=["author", "created_at"],
    name="tweet_author_created_idx",
)
```

Reason: Timeline filters by author and orders by newest tweets. PostgreSQL uses an ascending index with a backward scan for ORDER BY DESC.

Relations:

* `Tweet.author` uses `CASCADE`

---

## Follow

Fields:

* id
* follower_id
* following_id
* created_at

Constraints:

* unique `(follower_id, following_id)`
* self-follow prohibited

Index:

```python
models.Index(fields=["follower", "following"])
```

Relations:

* `Follow.follower` uses `CASCADE`
* `Follow.following` uses `CASCADE`

---

## Like

Fields:

* id
* user_id
* tweet_id
* created_at

Constraints:

* unique `(user_id, tweet_id)`

Index:

```python
models.Index(fields=["user", "tweet"])
```

Relations:

* `Like.tweet` uses `CASCADE`
* `Like.user` uses `CASCADE`

Self-like: Allowed.

Reason: The challenge does not prohibit self-like. Blocking it adds conditional logic without evaluation value. The critical constraint is preventing duplicate likes.

---

# Authorization Strategy

Authorization is enforced at query level.

Preferred pattern:

```python
tweet = get_object_or_404(
    Tweet,
    pk=pk,
    author=request.user
)
```

Required tests:

* user cannot delete another user's tweet
* unauthorized deletion does not remove tweet from database
* anonymous create tweet redirects to login with `next`
* anonymous follow redirects to login
* anonymous like redirects to login

---

# Timeline Strategy

## Behavior

Timeline contains:

* current user's own tweets
* tweets from followed users

Order: `created_at DESC`

Page size: 20 tweets

## Query Strategy

Timeline must use:

```python
select_related("author")
```

Like counts must use annotations or aggregation.

Templates must not execute per-row queries.

## Performance Contract

Process:

1. Implement timeline.
2. Measure actual query count using `connection.queries` or Django Debug Toolbar.
3. Freeze the explicit number in the test.
4. Do not use placeholder values.

Example:

```python
with self.assertNumQueries(4):
    response = self.client.get(reverse("timeline"))
```

Required performance tests:

* timeline returns first 20 tweets
* query count is bounded for first page
* adding tweets beyond page size does not increase query count
* no N+1 author queries

## Known Limitation

Offset pagination is used.

Trade-off: Cursor pagination would be preferable in production to avoid duplicate or skipped records during concurrent writes. Documented in README.

---

# Feature Specifications

## Registration

Fields: email, username, password

Validations:

* unique email
* unique username
* password required

After registration: `display_name = username` when not provided.

---

## Login

User may login using username or email.

Session created on success.

---

## Logout

Session destroyed.

Authenticated-only pages redirect after logout.

---

## Profile

Displays:

* username
* display name
* bio
* avatar placeholder (initials)
* followers count
* following count
* recent tweets

---

## Create Tweet

Requirements:

* max 280 characters
* backend validation required
* appears after creation
* HTMX submission preferred

Character counter:

* implemented for UX
* backend validation tested
* counter JavaScript does not require dedicated tests

---

## Delete Tweet

Requirements:

* owner only
* hard delete
* authorization enforced by filtered queryset

Implementation:

Use a POST route for deletion. HTML forms do not support DELETE natively. HTMX `hx-delete` adds friction with Django CSRF and redirects. A POST to `/tweets/<id>/delete/` is more idiomatic Django and simpler to test.

UX:

* authorized delete: redirect to timeline
* unauthorized delete: return `403 Forbidden`
* no raw Django error page shown to user

---

## Follow / Unfollow

Implementation:

Use POST routes for follow and unfollow.

* `/users/<username>/follow/` — POST to follow
* `/users/<username>/unfollow/` — POST to unfollow

Self-follow: blocked, returns `400 Bad Request`.

Duplicate follow: idempotent, no duplicate relationship created.

Unfollow nonexistent relationship: idempotent, no server error.

Required tests:

* self-follow blocked
* duplicate follow blocked
* unfollow nonexistent relationship does not error

---

## Like / Unlike

Implementation:

Use POST routes for like and unlike. Do not use `hx-delete` for unlike.

* `/tweets/<id>/like/` — POST to like
* `/tweets/<id>/unlike/` — POST to unlike

Duplicate like: no duplicate like created.

Self-like: allowed.

Unlike nonexistent like: idempotent, returns redirect or `200`, like count unchanged.

Required tests:

* duplicate like blocked
* self-like allowed
* unlike nonexistent like does not error

---

## Search

Search fields: username, display_name

Results include: username, display name, profile link, follow/unfollow button.

---

# Responsive Design Strategy

Every template must be mobile-first from first implementation.

Breakpoints:

* Mobile: below 640px
* Tablet: 640px to 1024px
* Desktop: above 1024px

Minimum test widths: 320px, standard mobile, tablet, desktop.

Visual polish is secondary to usability.

---

# Template Strategy

`base.html` must be created at step 6, before authentication templates.

Responsibilities:

* responsive navigation
* authenticated navigation states (login/logout links)
* page container
* mobile layout structure

All templates must extend:

```html
{% extends "base.html" %}
```

from their first implementation.

## CDN Loading Order

In `base.html`, CDN scripts must be loaded in `<head>` before any HTMX triggers:

```html
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/htmx.org@2.0.4"></script>
```

Keep the browser console open during development. If a "Blocked by CSP" or "htmx is not defined" error appears, the script load order or a browser extension is the cause. Do not add Django security headers (`SECURE_CONTENT_TYPE_NOSNIFF`, `Content-Security-Policy`) that restrict third-party CDN loading during this challenge.

## Avatar Placeholder Validation

During step 6 (`base.html`), visually verify the avatar with these inputs before continuing:

* Single character: `"A"`
* Two characters: `"Jo"`
* Name with space: `"Juan Pablo"`

`{{ user.display_name|slice:":2"|upper }}` produces `"A"`, `"JO"`, `"JU"` respectively. All are valid.

No dedicated test required for the avatar. Do not add coverage for this. Visual verification during template development is sufficient.

---

# Seed Strategy

Seed command required and idempotent.

Safe reset approach:

```python
from django.db import transaction

class Command(BaseCommand):

    @transaction.atomic
    def handle(self, *args, **options):
        User.objects.filter(
            email__endswith="@seed.example.com"
        ).delete()
        # ... create seed data ...
```

Use seed-specific email domains to avoid deleting real data.

Wrapping in `@transaction.atomic` ensures that if the seed is interrupted mid-run (e.g., `Ctrl+C`), the database rolls back to its previous state rather than being left in an inconsistent condition.

Generated data:

* at least 10 users
* at least 50 tweets
* follow relationships
* cross likes

Tool: Faker

Demo account:

```
email: demo@seed.example.com
password: password123
```

After seeding, the timeline must contain visible activity immediately.

## Seed Validation Rule

Run the seed command three consecutive times before advancing to the next build step.

All three runs must complete without errors.

The CASCADE delete on `User` propagates to Tweets, Follows, and Likes automatically.

This reset is safe for the challenge and demo environment. It must not be used against production data. If a real user were to follow a seed user, that relationship would also be deleted on reset — acceptable in a demo context, not in production.

---

# Testing Strategy

## Coverage

Target: 85%+
Internal floor: 80%
Submission standard: never below 85%

---

## Model Tests

User:

* unique email
* unique username
* display_name defaults to username

Tweet:

* max length validation
* cascade: deleting tweet deletes related likes

Follow:

* uniqueness constraint
* self-follow restriction
* cascade: deleting user removes follow relationships

Like:

* uniqueness constraint
* self-like allowed
* cascade: deleting tweet deletes related likes
* cascade: deleting user deletes their likes

---

## Integration Tests

Authentication:

* register
* login
* logout
* anonymous redirect includes `next` parameter

Tweets:

* create tweet
* delete own tweet
* reject deletion of foreign tweet (tweet remains in database)

Timeline:

* own tweets visible
* followed tweets visible
* unrelated tweets hidden
* paginated to 20

Social:

* follow
* unfollow
* self-follow blocked
* duplicate follow blocked
* unfollow nonexistent relationship does not error
* like
* unlike
* duplicate like blocked
* unlike nonexistent like does not error

Authorization:

* anonymous create tweet redirects to login
* anonymous follow redirects to login
* anonymous like redirects to login

Search:

* username search
* display_name search

---

## End-to-End Authentication Flow

Use Django Test Client.

Flow:

1. Register
2. Login
3. Access protected page (200)
4. Logout
5. Access same protected page (302 redirect to login)

---

## Performance Tests

Required:

* timeline query count frozen at measured value
* bounded query count with more than 20 tweets in database
* no N+1 author query regression

## Query Count Maintenance Rule

If a frozen query count changes, investigate before updating the number.

A changed count means either:

* a regression was introduced (fix the code)
* a deliberate feature was added (update the number and document why)

`base.html` must not execute database queries.
No context processors may query the database in this project.

---

# AI Engineering Workflow

AI is used as an engineering copilot, not an autonomous implementation system.

## Live AI Workflow Log

Maintain `AI_WORKFLOW.md` during development, not retrospectively.

Record immediately after finishing each feature:

```
Feature:
AI assistance used:
Human modifications:
Review findings:
```

Keep entries concise (3–5 bullets each).

Goal: capture real engineering judgment while context is fresh.

---

# Makefile

```makefile
check:
	@command -v docker >/dev/null 2>&1 || (echo "Docker not found" && exit 1)
	@docker compose version >/dev/null 2>&1 || (echo "Docker Compose plugin not found" && exit 1)
	@test -f .env || (echo ".env missing — run: cp .env.example .env" && exit 1)
	@echo "Environment ready."

setup: check
	docker compose build

migrate:
	docker compose run --rm web python manage.py migrate

seed:
	docker compose run --rm web python manage.py seed

up:
	docker compose up

test:
	docker compose run --rm web pytest

coverage:
	docker compose run --rm web pytest --cov=. --cov-report=term-missing
```

Recommended evaluator flow:

```bash
cp .env.example .env
make setup
make migrate
make seed
make up
```

## Manual Commands (Makefile fallback)

If `make` is unavailable (some Windows environments), use these equivalent commands directly:

```bash
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed
docker compose up
docker compose run --rm web pytest
docker compose run --rm web pytest --cov=. --cov-report=term-missing
```

---

# Documentation Requirements

## README.md

Must include a note at the top of the Runbook section:

```
This application requires authentication for all routes.
After running the seed, use the demo credentials below to access the app.
```

Must also include:

* stack justification
* exact prerequisites (runtime versions, Docker version)
* environment variables (full list with descriptions)
* installation commands
* migration commands
* seed command
* development run command
* test command
* coverage command
* demo credentials
* architecture explanation
* timeline explanation (query strategy, known pagination limitation)
* authentication explanation (session-based, no external providers)
* known limitations
* AI usage explanation

## DECISIONS.md

Must document:

* Django + HTMX over React (tradeoff: SPA flexibility vs delivery speed)
* Session auth over JWT (rationale: monolith with SSR has no JWT advantage)
* Authenticated-only application (rationale: simplifies authorization)
* AbstractUser custom model (rationale: migration safety, single table)
* Offset pagination (rationale: simplicity; cursor pagination documented as better for production)
* Self-like allowed (rationale: not prohibited, adds complexity without value)
* Docker Compose as selected bonus (rationale: evaluator experience, deployment awareness)
* Avatar as CSS initials (rationale: no storage needed, meets spec requirement)
* Tailwind via CDN (rationale: no npm pipeline in 72-hour window; production would use compiled build)
* HTMX via CDN (rationale: no frontend build tooling required; reduces Docker complexity)

## AI_WORKFLOW.md

Written live during development.

Maximum five entries covering:

1. Authentication
2. Tweets + Timeline
3. Social (Follow + Like)
4. Testing
5. Docker + Documentation

Format:

```
Feature:
AI assistance used:
Human modifications:
Review findings:
```

Quality over quantity. Five honest entries are more valuable than twenty generic ones.

## .env.example

Must be complete.

Evaluator must be able to run `cp .env.example .env` without editing.

---

# Build Order

1. Scaffold Django project
2. Configure environment variables (`python-decouple`, `.env.example`)
3. Add Docker skeleton (`Dockerfile`, `docker-compose.yml`, `Makefile`)
4. Create `accounts.User(AbstractUser)`, configure `AUTH_USER_MODEL`
5. Run initial migration inside Docker
6. Create `base.html` mobile-first layout
7. Implement authentication (register, login, logout)
8. Add authentication tests
9. Implement tweet model and creation
10. Add tweet tests
11. Implement timeline
12. Add timeline tests and query-count test
13. Implement follow system
14. Add follow tests
15. Implement like system
16. Add like tests
17. Implement search
18. Add search tests
19. Add seed command
20. Finalize README and DECISIONS.md — review and complete AI_WORKFLOW.md (written live during development, only finalized here)
21. Final coverage pass
22. Cleanup and bug fixes

Docker skeleton at step 3 means all subsequent `make migrate`, `make test`, and `make seed` commands run inside the container from the start.

## Commit Granularity for Steps 1–3

Steps 1–3 must produce at least three separate commits:

```
chore: initial django scaffold
chore: add dockerfile and docker-compose
chore: add makefile and environment configuration
```

Do not bundle these into one commit. The evaluator expects to see infrastructure layers built incrementally. This prevents late-stage surprises with database host, volumes, or settings incompatibilities.

The Docker skeleton at step 3 is minimal:

* `Dockerfile` with Python runtime and system dependencies
* `docker-compose.yml` with `web` and `db` services
* `Makefile` with all targets defined — introduced early and validated progressively as each dependency becomes available
* `requirements.txt` with all dependencies pinned

Full Docker validation happens at step 5 when the first migration runs inside the container.

## Dockerfile Requirements

The `Dockerfile` must include system dependencies for `psycopg2` or use `psycopg2-binary`:

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

`psycopg2-binary` is installed via `requirements.txt` — do not add a separate `pip install psycopg2-binary` line in the Dockerfile.

Missing `libpq-dev` causes `make migrate` to fail at step 5. Discover this at step 3, not step 19.

## requirements.txt

Must include before first Docker build:

```
Django>=5.0
psycopg2-binary
python-decouple
pytest
pytest-django
coverage
Faker
```

## Go/No-Go Gate at Step 3

Before proceeding to step 4, verify:

* `docker compose build` completes without errors
* `docker compose up` starts without errors
* A basic Django response is reachable at `http://localhost:8000`

If this takes more than 15 minutes, stop and fix the container environment. Do not proceed to authentication until the containerized environment works.

**After step 18: no new product features.**

Remaining effort after step 18 goes exclusively to:

* bug fixing
* coverage
* documentation
* evaluator experience

---

# Definition of Done

The project is complete when:

* All mandatory features work.
* Backend coverage is 85%+.
* Integration tests pass.
* Auth E2E flow passes.
* Performance tests pass.
* Seed command is idempotent and works.
* Docker Compose works.
* `make check`, `make migrate`, and `make seed` complete successfully.
* `make up` starts the application without errors.
* README is complete.
* DECISIONS.md is complete.
* AI_WORKFLOW.md is complete.
* `.env.example` is complete.
* Application is usable on mobile at 320px width.
* Git history is coherent with tests near the features they validate.
* Evaluator can run the project using only the documented runbook.

---

# Freeze Rule

This specification is frozen.

Implementation problems are resolved in code.

Architectural changes after this version are not permitted.