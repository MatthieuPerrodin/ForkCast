# ForkCast

A meal-planning app for a household, built around one idea: **know what to eat and what to buy,
without overthinking it.**

Most recipe apps stop at being a digital recipe box. ForkCast is designed around a **bidirectional
loop** between recipes, the pantry, and the shopping list:

- **"I have this at home, what should I cook?"** — suggestions filtered by prep time and
  nutritional balance, weighted to avoid repeating recently cooked recipes.
- **"What should I buy and cook this week?"** — the same loop run in reverse, eventually factoring
  in store discounts.

The project is documented end-to-end in [`docs/`](docs/): requirements, data model, tech stack,
and a task-by-task breakdown of what's built and what's next.

## Status

Phase 1 (recipe management) is in progress. See [docs/04-phase1-tasks.md](docs/04-phase1-tasks.md)
for the exact, up-to-date state — implemented so far:

- Recipe CRUD (create/edit/delete) with dynamic ingredient and step sub-forms (htmx, no page
  reloads)
- Serving-size adjustment that recalculates ingredient quantities client-side
- "Surprise me": a filtered, anti-repetition random recipe suggestion — the app's headline feature
  in its first, simplest form

The full roadmap (meal planning, shopping list, pantry tracking with expiry dates, and eventually
AI-assisted pantry input) lives in [docs/01-requirements.md](docs/01-requirements.md).

## Tech stack

| Layer | Choice |
|---|---|
| Language / framework | Python, Django (server-rendered monolith) |
| Frontend interactivity | Django templates + htmx + Alpine.js (no SPA, no JS build step) |
| Database | PostgreSQL via Supabase |
| File storage | Supabase Storage |
| Hosting | Google Cloud Run |

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

## Project documentation

- [docs/01-requirements.md](docs/01-requirements.md) — vision, users, phased roadmap, user stories
- [docs/02-data-model.md](docs/02-data-model.md) — entities and relationships
- [docs/03-tech-stack.md](docs/03-tech-stack.md) — stack choices and the reasoning behind them
- [docs/04-phase1-tasks.md](docs/04-phase1-tasks.md) — granular task checklist for the current phase

The UI itself is in French — this is a real app built for a French-speaking household — while the
codebase, comments, and documentation are in English.
