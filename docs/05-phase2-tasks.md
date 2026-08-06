# ForkCast — Phase 2: task breakdown

> Derived from [01-requirements.md](01-requirements.md) (Phase 2 user stories) and
> [02-data-model.md](02-data-model.md) (`MealSlot`).

## Design choice

A `MealSlot` row only exists once a recipe is actually assigned to a (date, meal_time) pair —
`unique_together` on those two fields. "Unplanned" is simply the absence of a row, rather than a
row with a nullable recipe. Simpler than the data model doc's literal nullable-FK sketch, same
observable behavior. Removing a recipe from a slot deletes the row; "replacing" is clear + assign
again rather than a dedicated swap action, to keep the first version simple.

## Tasks

- [x] T21 — `MealSlot` model (date, meal_time enum lunch/dinner, recipe FK, planned_servings),
      `unique_together` on (date, meal_time), admin registration, migration.
- [x] T22 — Weekly calendar view: 7 days (Monday-Sunday) x 2 meal times, addressed by ISO
      year/week in the URL (`/planning/<year>/W<week>/`), `/planning/` redirects to the current
      week.
- [x] T23 — Assign a recipe to a slot (inline form per empty slot: pick a recipe + servings,
      defaults to the recipe's `default_servings` if left blank).
- [x] T24 — Remove a recipe from a slot; re-assigning an already-planned slot replaces it in place
      (`update_or_create`, verified no duplicate row is created).
- [x] T25 — Week navigation (previous/next), using `date.fromisocalendar`/`isocalendar()` for the
      week arithmetic rather than hand-rolled date math.
- [x] T26 — Nav link to the planning page from the main layout.
- [x] T27 (added, not in the original breakdown) — Real automated test suite
      (`recipes/tests.py`, 15 tests via `manage.py test`), covering recipe CRUD, Surprise-me, and
      meal planning. Closes a gap flagged explicitly: every feature so far had only been verified
      manually (curl/Playwright/one-off scripts) and thrown away afterward, so regressions had no
      safety net going forward.

## Notes

- No htmx partial updates for this first version — plain POST/redirect/GET per action, consistent
  with recipe delete. Revisit only if the full-page reload feels clunky in practice.
- Out of scope for Phase 2 (per requirements §8 and the phased roadmap): shopping list generation
  from the plan (Phase 3), anything related to stock/pantry (Phase 4).
