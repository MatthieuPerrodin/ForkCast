# AGENTS.md — ForkCast

## Project status

- Django project `forkcast` (app `recipes`) bootstrapped and functional: models, admin, auth
  (native Django login/logout), recipe list/detail views. See Milestones 1.0/1.1 checked off in
  [docs/04-phase1-tasks.md](docs/04-phase1-tasks.md) for the exact state of Phase 1 —
  **always check that file before assuming a feature exists or not.**
- `legacy/` contains the **old, abandoned Django prototype** (`core/`, `myrecipes/`, hand-rolled
  auth, empty `core/models.py`) — kept for reference but irrelevant going forward. Do not use it
  as a reference for architecture or conventions.
- The source of truth for requirements, data, and stack lives in `docs/`:
  - [docs/00-journal-de-bord.md](docs/00-journal-de-bord.md) — chronological journal of decisions
    made, their reasoning, and lessons learned. Serves as an end-to-end project case study for the
    user. **Intentionally excluded from the git repo** (listed in `.gitignore`, considered
    personal by the user) — the file exists and must keep being updated locally, it must simply
    never be added/committed/pushed. It stays in French (personal, never published) even though
    the rest of the repo is in English.
  - [docs/01-requirements.md](docs/01-requirements.md) — vision, users, phased roadmap, user
    stories, out of scope.
  - [docs/02-data-model.md](docs/02-data-model.md) — entities, relationships, open questions.
  - [docs/03-tech-stack.md](docs/03-tech-stack.md) — validated stack: Python/Django (server-
    rendered monolith) + htmx/Alpine.js + PostgreSQL/Storage via Supabase + hosting on Google
    Cloud Run.
  - [docs/04-phase1-tasks.md](docs/04-phase1-tasks.md) — task checklist for Phase 1, check off /
    update as real progress happens (source of truth for what's actually done).
  - [docs/08-backlog-roadmap.md](docs/08-backlog-roadmap.md) — the Phase 5/backlog ideas from
    `01-requirements.md`, ordered simplest → most complex. **When there's no explicit task queued
    and the user wants to keep going, pick the next unclaimed item from the top of this file**
    rather than asking what to build or picking arbitrarily. Keep it in sync when backlog items are
    added, reordered, or shipped.
- **Read these documents before proposing code, an architecture, or a data model.**
- **After any structuring decision** (stack choice, architecture change, scope added/removed,
  lesson learned from a mistake): add an entry to `docs/00-journal-de-bord.md` (date,
  context/decision, why, lesson if relevant) before moving on. Don't wait until the end of the
  project to document — that defeats the whole point of the journal.
- **Language split**: code, comments, docs, commit messages, and this file are in English. The
  app's user-facing UI (templates' visible text, labels, buttons, messages) stays in **French**,
  because the household actually using this app is French-speaking (Québec). Don't translate
  template copy to English, and don't leave French leaking into Python identifiers, URL names, or
  comments — see [docs/00-journal-de-bord.md] for why this split exists.

## How to work on this repo

- **Mandatory git workflow for any significant change** (a feature, a milestone from the phase
  plan, a structuring change):
  1. Create a dedicated branch from `master` (e.g. `feature/recipe-form`,
     `feature/surprise-me`) — never commit directly to `master`.
  2. Build it, then **actually test it** before opening the PR (verify the relevant critical path
     — see the verification rule below — not just `manage.py check`).
  3. Open a Pull Request on GitHub (`gh pr create`) describing what changes and why.
  4. **Wait for the CI check to pass** (`.github/workflows/ci.yml`: `manage.py check` + the full
     test suite + `collectstatic`) — check with `gh pr checks <number>`, don't just assume it's
     green. A red check means something regressed; fix it on the branch before merging.
  5. Merge the PR (`gh pr merge`) once CI is green and reviewed/validated, then delete the branch.
  - For an isolated trivial fix (typo, doc), the full cycle isn't required — but when in doubt,
    apply it rather than pushing straight to `master`.
  - **Escape hatch**: if CI itself is broken by a GitHub-side outage (not the code) —
    confirmed by an explicit infra error like "Service Unavailable" resolving actions or "job
    was not acquired by Runner ... even after multiple attempts", not just a slow queue — it's
    fine to merge on local `manage.py test` results after checking with the user. Don't assume
    "probably just a blip" without that kind of explicit error message; this happened once
    (2026-08-06, PR #9) and is documented in `docs/00-journal-de-bord.md`.
- **Automated tests live in `recipes/tests.py` and must stay real.** When adding a feature,
  convert whatever manual verification you did (curl, Playwright, a one-off script) into a
  committed test rather than throwing it away — that's the whole point of having CI. Don't let
  `tests.py` go stale while verification happens ad hoc elsewhere.
- The stack (above) is validated — stick to it. If an architecture or tooling change seems needed
  along the way, discuss it with the user before implementing, and document the decision in
  `docs/03-tech-stack.md` plus a journal entry.
- Any new feature must map to an existing phase (1 to 5) of the requirements doc. If it doesn't,
  add it to the documentation first (backlog or new user story) before writing code.
- The project targets real use by one household with a **single shared account** (no multi-
  tenancy, no per-member permissions) — avoid over-engineering user scoping or roles/permissions.
- The product's core feature is the bidirectional meal-planning ↔ grocery loop (see requirements
  doc, section 5) — when in doubt about a feature's priority, this one comes first.
- Useful commands (venv in `.venv/`):
  - Run the server: `.venv/Scripts/python.exe manage.py runserver`
  - Migrations: `.venv/Scripts/python.exe manage.py makemigrations` then `migrate`
  - Local dev account (SQLite, not committed): `famille` / `forkcast-dev`
  - Automated tests: `recipes/tests.py` (`manage.py test`), run automatically in CI (see below).
- **Deployment is deliberately deferred** (explicit user decision, 2026-08-06): build out the
  phased roadmap locally against SQLite first, deploy later once there's more to show. Don't
  push toward finishing the Supabase/Cloud Run setup unless asked — it's parked, not blocked.
- Deployment target when the time comes: Google Cloud Run, dedicated GCP project
  `forkcast-mp-2026` (billing linked, Cloud Run/Cloud Build/Artifact Registry APIs enabled).
  `Dockerfile` builds and runs correctly (verified locally with `docker build` + `docker run` +
  `docker exec ... migrate` + real HTTP requests) but **has not been deployed yet** — Cloud Run has
  no persistent disk between instance restarts, so deploying with SQLite would silently lose data.
  Don't run `gcloud run deploy` until `DATABASE_URL` points at a real Supabase Postgres instance.
  Storage: recipe photos default to
  local filesystem storage; setting `SUPABASE_STORAGE_BUCKET` (+ the other `SUPABASE_STORAGE_*`
  vars, see `.env.example`) switches to Supabase Storage via `django-storages` — implemented but
  **not yet verified against a real bucket**, since no Supabase project exists yet for this
  project. See `docs/04-phase1-tasks.md` (T18/T19, "Blocked on the user") for what's left.
- After any change to a view/template touching authentication or the recipe CRUD, actually verify
  the critical path (POST login + page rendering, not just the absence of a server startup error)
  before considering the task done.
- **Adding a link to `templates/base.html`'s nav requires a mobile check of the nav itself**, not
  just the new page. It grew from 2 links to 6 across 2026-08-06 without anyone re-checking it fit
  on a phone screen — it didn't, and the fix was only caught by a dedicated responsive pass much
  later. A `flex-wrap` rule on the nav already handles reasonable growth, but re-verify at 375px
  after adding another item anyway.
- **Static files use `ManifestStaticFilesStorage` (via whitenoise) only when `DEBUG=False`** (see
  `forkcast/settings.py`, `STATICFILES_BACKEND`) — that backend needs `collectstatic` to have run
  first to build its filename-hash manifest, which isn't true for local `runserver` or the test
  suite. Local/test runs use plain `StaticFilesStorage` instead. If you add a new `{% static %}`
  reference and see `ValueError: Missing staticfiles manifest entry`, that's this — don't "fix" it
  by running `collectstatic` locally, the DEBUG branch already avoids needing it.
- **CSS gotcha for `<a role="button">`**: don't add a bare `a { color: ... }` override without
  excluding `[role="button"]` — button-styled links (`.pill`-adjacent, "Modifier", etc.) must keep
  the button color rule winning, or their text can end up the same color as their own background
  (found in dark mode, 2026-08-06). The current rule already does this
  (`a:not([role="button"])`); keep that exclusion if you touch link colors again.
- **Never wrap a `<form>` inside a `<p>`** — browsers implicitly close an open `<p>` when they hit a
  nested `<form>` (it's in the HTML5 list of paragraph-closing elements), silently breaking any
  "same row" layout you intended. Use a `<div>` (see `.button-row` in `app.css`) for any row mixing
  a link/button with a form.

## History

- 2026-08-05: restarted the project from scratch on the product/requirements side; requirements,
  data model, and tech stack validated the same day (see `docs/00-journal-de-bord.md`);
  bootstrapped the `forkcast` Django project with Phase 1 Milestones 1.0 and 1.1 completed and
  verified end-to-end. The old prototype is archived in `legacy/`. The Django app and models were
  originally named in French (`recettes`, `Recette`, `Etape`...) and renamed to English
  (`recipes`, `Recipe`, `Step`...) the same day once the repo was made public, to keep the
  codebase professional while the UI stayed French for the household using it.
