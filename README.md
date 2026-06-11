# Twitter Clone

A full-stack Twitter-like web application built with Django, PostgreSQL, and HTMX. Developed as a focused challenge deliverable emphasising testability, documentation quality, and engineering decision visibility.

---

## Stack

| Layer | Technology | Reason |
|-------|-----------|--------|
| Backend | Django 6.x | Batteries-included: ORM, auth, admin, forms |
| Templates | Django Templates + HTMX 2.0 via CDN | Server-side rendering with progressive enhancement; no npm pipeline |
| Styling | Tailwind CSS via CDN | Mobile-first utility classes; no build step required in a 72-hour window |
| Database | PostgreSQL | Relational integrity, `CHECK` constraints, index support |
| Auth | Django sessions | Native fit for an SSR monolith; no JWT overhead |
| Testing | pytest + pytest-django + coverage | Fast, Pythonic test runner with fixture support |
| Infra | Docker Compose | Reproducible environment; zero local Python/PostgreSQL setup |

---

## Prerequisites

- Docker Desktop ≥ 24 (includes Compose v2)
- `make` (optional — manual commands listed below)
- Internet access (Tailwind CSS and HTMX are loaded from CDN)

No local Python or PostgreSQL installation required.

---

## Environment Variables

All configuration is read from a `.env` file at the project root.

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | _(required)_ | Django secret key |
| `DEBUG` | `False` | Enable debug mode |
| `DATABASE_URL` | _(required)_ | PostgreSQL connection string |
| `ALLOWED_HOSTS` | `localhost` | Comma-separated list of allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | `http://localhost:8000` | Comma-separated trusted origins for CSRF |

The `.env.example` file contains working values for local Docker development. No edits are needed.

---

## Runbook

> **Authentication note:** This application requires authentication for all routes.
> After running the seed, use the demo credentials below to access the app.

### 1. Set up environment

```bash
cp .env.example .env
```

### 2. Build the container

```bash
make setup
# or: docker compose build
```

### 3. Apply migrations

```bash
make migrate
# or: docker compose run --rm web python manage.py migrate
```

### 4. Seed demo data

```bash
make seed
# or: docker compose run --rm web python manage.py seed
```

### 5. Start the application

```bash
make up
# or: docker compose up
```

Visit **http://localhost:8000**

### Demo credentials

```
Email:    demo@seed.example.com
Password: password123
```

---

## Tests

```bash
make test
# or: docker compose run --rm web pytest
```

## Coverage

```bash
make coverage
# or: docker compose run --rm web pytest --cov=. --cov-report=term-missing
```

Current coverage: **91%** (198 tests).

---

## Architecture

```
twitter_clone/          Django project root (settings, root URL conf)
accounts/               Custom user model, auth views, follow system
  models.py             User (AbstractUser), Follow
  views.py              register, login, logout, profile, follow, search
  backends.py           EmailOrUsernameBackend (login by email OR username)
  forms.py              RegisterForm, LoginForm, ProfileEditForm
tweets/                 Tweet + Like models, timeline, CRUD views
  models.py             Tweet, Like
  views.py              timeline, tweet_create, tweet_delete, like, unlike
templates/              All HTML templates (extends base.html)
  base.html             Navigation, CDN scripts, responsive layout
```

### Custom user model

`accounts.User` extends `AbstractUser` and adds `email` (unique), `display_name`, and `bio`. Configured as `AUTH_USER_MODEL` before the first migration — changing this after migrations exist causes irreversible breakage.

### Authentication backend

`EmailOrUsernameBackend` allows login with either a username or email address. It falls back to Django's `ModelBackend` behaviour for permission checks.

### Timeline query strategy

The timeline view issues **4 SQL queries** per page load:

1. Session lookup
2. User lookup
3. `COUNT(*)` for the paginator
4. Tweet page with annotations

Annotations are compiled into a single SQL statement:

```python
Tweet.objects
    .select_related("author")           # eliminates N+1 author lookups
    .annotate(
        like_count=Count("likes"),      # LEFT JOIN aggregate
        user_liked=Exists(              # correlated subquery in SELECT
            Like.objects.filter(user=request.user, tweet=OuterRef("pk"))
        ),
    )
    .order_by("-created_at")
```

`select_related("author")` eliminates the N+1 author query. `Count` and `Exists` both compile into the same SQL statement — not additional queries.

### Pagination limitation

Offset-based pagination (`django.core.paginator.Paginator`) is used. In a high-write production system, concurrent inserts can cause a tweet to appear on two pages or be skipped entirely as the user navigates. Cursor-based pagination would eliminate this; it was not implemented here because the spec documents the trade-off and targets demonstrability over production hardening.

### Session authentication

Django's built-in session framework stores a signed session cookie in the browser. All routes are protected with `@login_required`. There are no external auth providers, no JWT tokens, and no OAuth flows. `LOGIN_URL = "/login/"` ensures unauthenticated requests redirect with a `?next=` parameter so the user returns to the intended page after login.

---

## Known Limitations

- **Offset pagination:** tweets may shift between pages under concurrent writes (see above).
- **CDN dependency:** Tailwind CSS and HTMX are loaded from unpkg/CDN. The app is functional without them but unstyled.
- **No real-time updates:** timeline requires a manual refresh to show new tweets.
- **Seed data only:** the demo account and all seed users share the same password (`password123`) and are intended for evaluation only.
- **Self-like is allowed:** the spec does not prohibit it. See DECISIONS.md.

---

## AI Usage

Claude (Anthropic) was used as an engineering copilot throughout this project. See `AI_WORKFLOW.md` for a feature-by-feature breakdown of what was AI-generated, what was modified by human review, and what required hands-on debugging. No AI output was committed without review.
