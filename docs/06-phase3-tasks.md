# ForkCast — Phase 3: task breakdown

> Derived from [01-requirements.md](01-requirements.md) (Phase 3 user stories) and
> [02-data-model.md](02-data-model.md) (`ShoppingList`/`ShoppingListItem`, `Deal`).
>
> Split into two PRs: core shopping list first (this covers most of the user value), then the
> `Deal`/rabais angle (Direction B, §5) as a separate follow-up.

## Design choices

- **Single active list, not a history of lists.** The data model doc flags "one list at a time"
  as the starting assumption. Implemented literally: there is always exactly one `ShoppingList`
  (get-or-create the most recent one), not a new row per generation. Revisit only if the need for
  multiple parallel/historical lists shows up in practice.
- **Regenerating overwrites auto items, preserves manual ones.** "Generate from the week" deletes
  and recreates every `source=auto` item from scratch (so it always reflects the current plan
  exactly), but never touches `source=manual` items or their checked state — a manually-added
  item or a box the user already ticked shouldn't vanish because the plan changed elsewhere.
- **No unit conversion.** Aggregation only sums quantities for the same (ingredient, unit) pair,
  per the data model doc's deferred-conversion note. Same ingredient in two different units across
  recipes produces two separate line items rather than a guessed conversion.
- **Servings scaling.** Each `MealSlot.planned_servings` can differ from the recipe's
  `default_servings` (same mechanism as the per-recipe portion adjuster from Phase 1) — the
  aggregation scales each `RecipeIngredient.quantity` by `planned_servings / default_servings`
  before summing.
- **Aisle sorting for free**, since `Ingredient.aisle_category` already exists (Phase 1) and this
  was flagged as a cheap backlog idea in the requirements doc: list items are ordered by aisle.

## Tasks — core shopping list

- [x] T28 — `ShoppingList` + `ShoppingListItem` models (nullable `ingredient` FK +
      `free_text_name` for manual items, `quantity`/`unit`, `checked`, `source` enum), admin,
      migration.
- [x] T29 — "Generate from this week" action on the planning page: aggregates
      `RecipeIngredient`s across all of the week's `MealSlot`s, scaled by servings, grouped by
      (ingredient, unit); overwrites existing auto items as described above.
- [x] T30 — Shopping list page: check/uncheck an item, add a manual item (free text + optional
      quantity/unit), sorted by aisle category.
- [x] T31 — Nav link to the shopping list.
- [x] T32 — Automated tests: aggregation math (same ingredient/unit summed, different units kept
      separate, servings scaling), regeneration preserving manual items/checked state, check-off,
      manual add. 21/21 tests passing (6 new). Also spot-checked visually against the demo data
      (Carbonara's ingredients correctly appear after generating from a week with it planned).

## Tasks — Deal / rabais (Direction B V1, requirements §5)

- [x] T33 — `Deal` model (ingredient FK, store, sale_price, start/end date), admin. Built alongside
      the shopping list models in the previous PR.
- [x] T34 — Dedicated in-app form (`/deals/`) rather than pushing the household to `/admin/` for a
      feature they'll use directly — keeps the whole experience in French/consistent styling.
- [x] T35 — Badge (`🏷️ ingrédient en rabais`) on recipe cards in the list, and a `🏷️` prefix on
      on-deal recipes in the planning page's recipe picker. Both driven by one shared helper,
      `_recipes_on_deal_ids()`.
- [x] T36 — Automated tests: `is_active()` boundary dates (starts today, ends today, day before/
      after), flagging via the real list/planning views (`response.context["deal_recipe_ids"]`),
      expired deals correctly not flagging. 4 new tests (25 total). Also spot-checked visually:
      flagged Parmesan as on sale, confirmed the Carbonara card picked up the badge.

## Out of scope

Automatic flyer/circulaire fetching (Phase 5 backlog) — `Deal.source` isn't even modeled yet since
only manual entry exists; add it when Phase 5 actually needs to distinguish sources.
