# ForkCast

![CI](https://github.com/MatthieuPerrodin/ForkCast/actions/workflows/ci.yml/badge.svg)

A meal-planning app for a household, built around one idea: **know what to eat and what to buy,
without overthinking it.**

Most recipe apps stop at being a digital recipe box. ForkCast is designed around a **bidirectional
loop** between recipes, the pantry, and the shopping list:

- **"I have this at home, what should I cook?"** — suggestions filtered by prep time and
  nutritional balance, weighted to avoid repeating recently cooked recipes, and aware of what's
  actually in the pantry.
- **"What should I buy and cook this week?"** — the same loop run in reverse: plan the week,
  generate the shopping list, and factor in store discounts.

The project is documented end-to-end in [`docs/`](docs/): requirements, data model, tech stack,
and a task-by-task breakdown of what's built at each phase — including the *why* behind each
decision in [docs/00-journal-de-bord.md](docs/00-journal-de-bord.md) (kept locally, not published,
but its reasoning feeds every other doc).

## Status

**Phases 1 through 4 are done.** See the `docs/0X-phaseN-tasks.md` files for the exact, granular
state of each one. Built so far:

- **Recipes** — CRUD with dynamic ingredient/step sub-forms (htmx, no page reloads), serving-size
  adjustment that recalculates quantities client-side, search/filter by tag
- **Surprise me** — a filtered, anti-repetition recipe suggestion (prep time, nutrition score);
  the app's headline feature, direction A of the bidirectional loop
- **Meal planning** — a weekly calendar (lunch/dinner × 7 days) to assign recipes to slots
- **Shopping list** — generated from a week's plan, ingredient quantities aggregated and scaled by
  servings, automatically reduced by what's already in the pantry
- **Deals** — flag an ingredient on sale; recipes using it get highlighted on the recipe list and
  in the meal planner — direction B of the bidirectional loop
- **Pantry** — stock tracked as per-purchase lots with expiry dates, alerts for items expiring
  soon, and automatic FIFO deduction from stock when a recipe is marked as cooked

Automated tests (`recipes/tests.py`, run in CI on every PR) cover all of the above — 36 tests as of
this writing.

**Deployment is intentionally not live yet** — the app is being built out fully against local
SQLite first; see [docs/03-tech-stack.md](docs/03-tech-stack.md) for the target stack (Google Cloud
Run + Supabase) once that's picked back up.

## Tech stack

| Layer | Choice |
|---|---|
| Language / framework | Python, Django (server-rendered monolith) |
| Frontend interactivity | Django templates + htmx + Alpine.js (no SPA, no JS build step) |
| Database | PostgreSQL via Supabase (SQLite locally) |
| File storage | Supabase Storage |
| Hosting | Google Cloud Run |
| CI | GitHub Actions — tests + checks on every PR |

Full reasoning behind each choice: [docs/03-tech-stack.md](docs/03-tech-stack.md).

## Running it locally

```bash
python -m venv .venv
.venv/Scripts/activate        # or source .venv/bin/activate on macOS/Linux
pip install -e .
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

No `DATABASE_URL` is needed locally — the app falls back to SQLite automatically. Set
`DATABASE_URL` (see `.env.example`) to point at a Postgres/Supabase instance instead.

Run the test suite with `python manage.py test`.

## Project documentation

- [docs/01-requirements.md](docs/01-requirements.md) — vision, users, phased roadmap, user stories
- [docs/02-data-model.md](docs/02-data-model.md) — entities and relationships
- [docs/03-tech-stack.md](docs/03-tech-stack.md) — stack choices and the reasoning behind them
- [docs/04-phase1-tasks.md](docs/04-phase1-tasks.md) through
  [docs/07-phase4-tasks.md](docs/07-phase4-tasks.md) — granular task checklists per phase

The UI itself is in French — this is a real app built for a French-speaking household — while the
codebase, comments, and documentation are in English.
