# Architecture Decision Records

Each entry documents a decision made during this challenge, its rationale, and the trade-off accepted.

---

## 1. Django + HTMX over React

**Decision:** Use Django Templates with HTMX for all interactivity.

**Rationale:** React requires a separate build pipeline, a Node.js environment, API endpoints, and client-side state management. Inside a 72-hour challenge window, that overhead is a liability. Django Templates keep logic server-side, simplify testing (no API mocking), and reduce total moving parts. HTMX adds progressive enhancement (like button submits without full-page reload) without a JavaScript build step.

**Trade-off:** Single-page-app flexibility is sacrificed. Full-page navigations are visible on slower connections. A production product would likely use a proper React/Vue frontend once the team grew and the API surface was stable.

---

## 2. Session auth over JWT

**Decision:** Use Django's built-in session framework. No JWT.

**Rationale:** JWT has a clear advantage in stateless, horizontally-scaled API deployments where the resource server is separate from the auth server. This application is a server-side-rendered monolith. Django's session middleware is already present, handles CSRF natively, integrates with `@login_required`, and requires zero additional libraries. JWT would add complexity (token storage, refresh flows, expiry logic) with no architectural benefit here.

**Trade-off:** Sessions require sticky sessions or a shared session store (e.g., Redis) at scale. Acceptable in the challenge context; would need to be re-evaluated if horizontal scaling became a requirement.

---

## 3. Authenticated-only application

**Decision:** All routes require authentication. Unauthenticated requests redirect to `/login/?next=<path>`.

**Rationale:** The challenge evaluates core social features — timeline, follow, like, tweet. Differentiating public vs. private views adds conditional rendering logic, doubles the set of anonymous access tests, and introduces edge cases (e.g., what to show a logged-out visitor on a profile page). Requiring authentication for everything simplifies the authorization model, reduces test surface, and keeps every template consistent.

**Trade-off:** The application is not publicly discoverable — a real product would have public profiles and landing pages. Documented as a known limitation.

---

## 4. Custom AbstractUser from commit one

**Decision:** Define `accounts.User(AbstractUser)` before the first migration and set `AUTH_USER_MODEL = "accounts.User"` in settings.

**Rationale:** Django's `AUTH_USER_MODEL` cannot be safely changed after the initial migration without manually rewriting foreign key references across every table. Starting with `AbstractUser` costs nothing and gives full flexibility to add `email`, `display_name`, and `bio` to the same table without a separate `Profile` model or a `OneToOneField` join.

**Trade-off:** A `OneToOneField` profile model would be more modular. The single-table approach is faster to query and simpler to maintain at this scale.

---

## 5. Offset pagination

**Decision:** Use `django.core.paginator.Paginator` (offset/limit) for the timeline.

**Rationale:** Django's `Paginator` is built-in, requires no additional dependencies, and integrates with templates in three lines. The implementation matches what a senior Django developer would reach for first.

**Trade-off:** Cursor-based pagination is strictly better for feeds with concurrent writes — it prevents records from appearing twice or being skipped as new tweets arrive. Cursor pagination requires a stable sort key (e.g., `created_at` + `id`), a different URL scheme, and more complex query logic. The spec explicitly documents this trade-off and designates it as a known limitation rather than a required fix.

---

## 6. Self-like allowed

**Decision:** A user may like their own tweet. No constraint prevents it.

**Rationale:** The spec explicitly states "Self-like: Allowed." and explains the reasoning: the challenge does not prohibit it, and blocking it adds conditional logic in the view and template without meaningful evaluation value. The critical constraint — preventing duplicate likes — is enforced by a `UniqueConstraint` on `(user_id, tweet_id)`.

**Trade-off:** On a real platform, self-likes inflate engagement metrics and are typically blocked. Not applicable here.

---

## 7. Docker Compose as bonus feature

**Decision:** Include Docker Compose as the single planned bonus feature.

**Rationale:** The spec identifies four bonus criteria: evaluator value, low product complexity, runbook reliability, and deployment awareness. Docker Compose scores high on all four. An evaluator can run `cp .env.example .env && make setup && make migrate && make seed && make up` and have a working application without installing Python or PostgreSQL locally. The implementation cost (a `Dockerfile` + `docker-compose.yml` + `Makefile`) is low relative to the evaluator experience improvement.

**Trade-off:** Docker adds a layer of indirection when debugging — errors inside the container sometimes have less obvious stack traces. Worth it for reproducibility.

---

## 8. Avatar as CSS initials placeholder

**Decision:** Render avatars as a styled `div` showing the first two characters of `display_name`. No model field, no file storage, no image uploads.

**Rationale:** The spec requires an avatar placeholder, not real image uploads. A CSS div is zero-cost: no `MEDIA_ROOT`, no S3, no form field, no migration. The template filter `{{ user.display_name|slice:":2"|upper }}` is sufficient and handles single-character names gracefully.

**Trade-off:** All avatars look the same (same slate background). Acceptable for a challenge deliverable. Production would use an upload field and object storage.

---

## 9. Tailwind CSS via CDN

**Decision:** Load Tailwind from `https://cdn.tailwindcss.com` in `base.html`. No PostCSS, no purge, no `package.json`.

**Rationale:** The CDN Play CDN build compiles Tailwind on-the-fly in the browser. This removes the npm pipeline entirely — no `node_modules`, no watch process, no build step in Docker. Within a 72-hour window, eliminating an entire toolchain category is the right call.

**Trade-off:** The CDN build includes the full, unpurged stylesheet — much larger than a production compiled build. The spec acknowledges this: "Production would use a compiled build to strip unused classes. CDN is intentional for this challenge." The app also requires internet access for CDN assets; functionality remains usable without them but styling degrades.

---

## 10. HTMX via CDN

**Decision:** Load HTMX 2.0.4 from `https://unpkg.com/htmx.org@2.0.4` in `base.html`.

**Rationale:** HTMX has no build-time dependencies and is a single script tag. Loading it from CDN avoids adding a frontend build toolchain and keeps the Docker image simple. The pinned version (`@2.0.4`) prevents surprise breakage from upstream releases.

**Trade-off:** CDN availability is a runtime dependency. The progressive enhancement rule mitigates this: all HTMX-enhanced forms degrade to standard HTML POST submissions if HTMX fails to load. No interactivity is lost — only the no-full-reload UX enhancement.
