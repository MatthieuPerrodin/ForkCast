# ForkCast — Phase 1: task breakdown

> Derived from [01-requirements.md](01-requirements.md) (Phase 1 user stories) and
> [02-data-model.md](02-data-model.md). Stack: [03-tech-stack.md](03-tech-stack.md).

## Milestone 1.0 — Project bootstrap ✅

- [x] T1 — New Django project (`forkcast`) at the repo root, replacing the old prototype.
- [x] T2 — Environment-variable config (`.env`): `SECRET_KEY`, `DEBUG`, `DATABASE_URL`.
      Automatic switch between SQLite (local, zero setup) / PostgreSQL (as soon as `DATABASE_URL`
      points to Supabase).
- [x] T3 — `.gitignore` + git repo initialized.
- [x] T4 — Base template (`base.html`) with htmx + Alpine.js (CDN) + Pico.css (minimal styling, no
      build step), minimal layout.
- [x] T5 — Minimal auth: a single account, simple login page (Django's native `LoginView`/
      `LogoutView`, no signup, account created via `createsuperuser`).

## Milestone 1.1 — Recipe data model ✅

- [x] T6 — `Ingredient`, `Tag`, `Recipe`, `Step`, `RecipeIngredient` models (app `recipes`),
      matching [02-data-model.md](02-data-model.md). The conceptual `RecipeTag` join entity is
      implemented as a standard Django `ManyToManyField` rather than a separate model (carries no
      data of its own).
- [x] T7 — Initial migrations, applied and verified on local SQLite.
- [x] T8 — Registered in the Django admin (inlines for ingredients/steps directly on the recipe
      page).

## Milestone 1.2 — Recipe CRUD (user interface)

- [x] T9 — Recipe list view + search by name + filter by tag.
- [x] T10 — Recipe detail view + dynamic quantity adjustment based on desired servings
      (client-side recalculation via Alpine.js, no server round-trip).
- [x] T11 — Recipe creation form (title, description, photo, time, servings, tags) with a dynamic
      sub-form for ingredients (add/remove rows via htmx, using `inlineformset_factory` + dedicated
      htmx endpoints).
- [x] T12 — Dynamic sub-form for steps (add/remove, order).
- [x] T13 — Editing an existing recipe (reuses the same form/view as T11).
- [x] T14 — Deleting a recipe (JS `confirm()` before the POST).
- [ ] T15 — Photo upload — the field already exists (`ImageField` on `Recipe`, local storage via
      `MEDIA_ROOT`); switching to Supabase Storage is documented as a separate task (Milestone
      1.4) rather than a blocker here.

## Milestone 1.3 — Headline feature V1 (Direction A, see requirements §5)

- [x] T16 — `last_cooked_on` field + a "I cooked this" action to update it from the recipe page.
- [x] T17 — "Surprise me" view: filter by prep time and nutrition score, anti-repetition ordering
      (`nulls_first` on `last_cooked_on`, random draw among the 5 least recently cooked
      candidates).

## Milestone 1.4 — Polish

- [~] T18 — Supabase Storage backend implemented (`django-storages`, S3-compatible, env-var
      driven, local-filesystem fallback when unconfigured). **Not yet verified against a real
      bucket** — pending the user creating a Supabase project (Postgres + Storage bucket).
- [~] T19 — `Dockerfile` (gunicorn + whitenoise) written and verified end-to-end locally (build,
      migrate, login, static files all confirmed working inside the container via Docker). GCP
      project `forkcast-mp-2026` created, billing linked, Cloud Run/Cloud Build/Artifact Registry
      APIs enabled. **Actual `gcloud run deploy` still pending**: deploying now would mean SQLite
      on Cloud Run's non-persistent disk, which loses data on every instance restart -- not worth
      shipping until `DATABASE_URL` points to the real Supabase Postgres instance.
- [x] T20 — Responsive review (mobile 375px/desktop 1280px) of list/detail/form pages, checked
      with real Playwright screenshots + a horizontal-overflow assertion, not just a visual guess.
      Found and fixed a real bug (the ingredient table pushed the whole page wider than the
      viewport on mobile — wrapped it in an `overflow-x: auto` container instead), plus a
      usability polish on the headline "Surprise me" feature (its filter fields were legible but
      cramped/truncated on mobile — now stack vertically below 480px).

### Blocked on the user

T18/T19 need a Supabase project (Postgres database + a public `recipe-photos` storage bucket) that
doesn't exist yet. Steps to create it are in `docs/00-journal-de-bord.md` (also given to the user
directly in chat). Once `DATABASE_URL` and the `SUPABASE_STORAGE_*` vars are available, wire them
into a local `.env`, verify locally, then finish the Cloud Run deploy.

## Notes

- This document is a working checklist, not a fixed plan: check things off as they're done,
  add/remove tasks as the need evolves. Any decision that deviates from this plan should be
  tracked in [00-journal-de-bord.md](00-journal-de-bord.md).
