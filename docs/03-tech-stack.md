# ForkCast — Tech stack

> Status: validated with the user on 2026-08-05. Derived from the requirements
> ([01-requirements.md](01-requirements.md)) and the data model
> ([02-data-model.md](02-data-model.md)).

## 1. Overview

| Layer | Choice | Why |
|---|---|---|
| Language | Python | Familiarity from the previous prototype; solid ecosystem for potential AI features later (Phase 5). |
| Web framework | Django (server-rendered monolith) | Batteries included (ORM, admin, auth), a single project to maintain solo, naturally fits the relational data model. |
| Frontend interactivity | Django templates + htmx + Alpine.js | "Reactive app" feel (checkboxes, planning calendar) without building a separate SPA or a dedicated API. |
| Database | PostgreSQL via **Supabase** | Managed, generous free tier, the user already knows it (prior personal-finance project) — also includes file storage, reused for recipe photos. |
| File storage | Supabase Storage | Avoids adding one more service just for recipe photos; already bundled with Supabase. |
| App hosting | **Google Cloud Run** | Containerized (Docker), scales to zero (no cost at low usage), already used by the user on a previous project. |

## 2. Still open

- **Offline support for the shopping list (Phase 3)**: undecided. The chosen architecture doesn't
  close this door — a *manifest.json* + a *service worker* scoped to the shopping list page can be
  added later without re-architecting the rest.
- **Unit conversion** (see data model §5): remains an implementation detail to handle when coding
  recipes/shopping, not a stack concern.

## 3. Alternative considered and rejected

**FastAPI + a separate frontend (React/Vue)** — more "modern" on paper, but means two codebases to
maintain for a solo developer, with no real benefit for this project (no real-time or native
mobile need that would justify the added complexity). Rejected in favor of a Django monolith.

## 4. Concrete technical components

- Django project (`forkcast`), app `recipes`.
- Dependencies declared in `pyproject.toml` (see the file at the project root).
- `Dockerfile` for deployment to Cloud Run.
- Connection to the Supabase Postgres database via environment variables (no hardcoded secrets,
  see non-functional requirements in the requirements doc §7).
- `django-htmx` + Alpine.js loaded from a CDN, no complex JS build step (no webpack/vite needed to
  get started).

## 5. Next step

Work through the remaining Phase 1 tasks — see [04-phase1-tasks.md](04-phase1-tasks.md).
