# ForkCast — Requirements

> Status: validated. Data model, tech stack, and Phase 1 implementation are underway — see
> [02-data-model.md](02-data-model.md), [03-tech-stack.md](03-tech-stack.md), and
> [04-phase1-tasks.md](04-phase1-tasks.md).

## 1. Project vision

ForkCast is an app that simplifies a household's daily food routine: **knowing what to eat and
doing groceries without spending time on it or overthinking it**. It centralizes recipes, plans
meals, generates the shopping list, and tracks what's in stock at home.

**Headline feature**: a **bidirectional** meal ↔ grocery loop, in both possible directions,
prioritized by **nutritional quality** and **prep speed**:
- *"I have this at home, what should I cook?"* (from the pantry)
- *"What should I buy and cook this week?"* (ideally factoring in store discounts/promotions)

This is the thread that ties recipes, the pantry, meal planning, and the shopping list together;
it is not a secondary feature bolted on at the end (details in §5).

## 2. Context & motivation

- Personal project, both a **practical tool** (real daily use) and a **learning project** (a
  chance to properly explore architecture, technical choices, and good practices).
- Complete restart of a previous attempt: the old codebase (Django, basic auth, no domain model)
  was set aside. Rebuilding from requirements first this time.

## 3. Target users

- A single household/family.
- **One single shared account** — no distinction between household members, no differentiated
  permissions. Everyone sees and edits the same data (recipes, planning, stock).
- Expected use on desktop (entering recipes, planning) and on mobile (checking recipes in the
  kitchen, shopping list at the store) → the interface must be comfortably usable on both.

## 4. Functional scope — phased roadmap

The app is split into independently shippable phases, so there's a usable tool as early as Phase 1
rather than waiting for one big release.

### Phase 1 — MVP: Recipe book
Manage and browse recipes. This is the foundation every later phase depends on.

### Phase 2 — Meal planning
Organize a weekly meal calendar by assigning existing recipes to days/slots (lunch/dinner).

### Phase 3 — Shopping list
Automatically generate an aggregated shopping list from the week's meal plan (or a selection of
recipes), combining the needed ingredients.

### Phase 4 — Pantry
Track what's in stock at home: ingredients on hand, **quantities**, **expiry dates** (pantry,
fridge, freezer). The Phase 3 shopping list should be able to subtract what's already in stock.

### Phase 5 — AI / external data exploration (backlog, not prioritized)
Ideas to reduce data-entry friction and enrich the meal ↔ grocery loop, all dependent on an
external data source or AI processing — hence more uncertain and only worth tackling once phases
1-4 are stable and the need has been proven through actual use:
- Photo-based product recognition for the pantry.
- Receipt scanning/OCR to automatically restock the pantry after a grocery run.
- Automatically fetching store discounts/flyers (scraping or an API like Flipp/Reebee) to
  proactively suggest what to buy — see Direction B in §5.

## 5. Headline feature: bidirectional meal ↔ grocery loop

The real need isn't "having a recipe book" but "knowing what to eat and what to buy, without
overthinking it" — and that works in both directions.

### Direction A — "I have this at home, what should I cook?"
- **V1 (from Phase 1 onward, no need to wait for the pantry)**: from the recipe book, suggest a
  recipe (or a short-list) filtered/sorted by prep time and nutrition tag (e.g. "quick",
  "balanced"), with a "Surprise me" button that respects the active filters. Avoids repetition by
  deprioritizing recently cooked recipes.
- **V2 (once the pantry is in place, Phase 4)**: cross-reference recipes against actual stock on
  hand to prioritize the ones where most ingredients are already at home, still weighted by speed
  and nutritional quality. This is the "complete" version of this direction.

### Direction B — "What should I buy and cook this week?"
- **V1 (manual, from Phase 3 Shopping list onward)**: the user manually flags which ingredients
  are on sale this week (and optionally the sale price, from checking the flyer themselves). The
  app highlights recipes that use those ingredients when planning/generating the shopping list.
- **V2 (backlog, Phase 5, ambitious)**: automatically fetching store flyers/discounts to
  proactively suggest what to buy and cook, with no manual entry. Depends on a reliable data
  source on the grocery side (scraping or an API) — comparable in complexity to receipt OCR, to be
  evaluated when the time comes rather than assumed upfront.

### Ideas inspired by existing apps (backlog, to be sorted)

To evaluate over time, once phases 1-4 are stable — offered for inspiration, none of these are
committed to yet:

- **Shopping list sorted by store aisle** (produce, pantry, frozen...) to move faster through the
  store — cheap to build now by adding a "category" field to the ingredient reference table (see
  data model).
- **Recipe import from a URL** (often just copy-pasted from a site) — avoids manual re-entry,
  a big time saver for filling the recipe book initially.
- **Leftover management**: "I have X grams of Y left, what can I make with it?" — a targeted
  variant of the meal suggestion feature.
- **Diet/allergy filters** (vegetarian, gluten-free...) applied to suggestions and shopping list
  generation.
- **Rotation/anti-repetition**: avoid suggesting the same recipe 3 times in a week.
- **Simple nutrition score or label** per recipe (e.g. Nutri-Score-inspired) rather than a full
  calorie calculation — stays simple to enter and maintain.
- **Expiry notifications** ("this expires in 2 days, cook it") — tied to Phase 4.
- **Cost estimate** for groceries — useful but not a priority compared to nutrition/speed.

## 6. Detailed functional requirements (user stories)

### Phase 1 — Recipes
- As a user, I can create a recipe with: title, photo (optional), ingredient list (name,
  quantity, unit), prep steps, prep/cook time, number of servings.
- As a user, I can edit or delete an existing recipe.
- As a user, I can browse my recipe list and open one recipe's detail.
- As a user, I can search/filter my recipes (by name, by tag/category — e.g. "vegetarian",
  "quick", "dessert").
- As a user, I can adjust a recipe's displayed quantities based on a desired number of servings.

### Phase 2 — Meal planning
- As a user, I can see a weekly meal calendar (lunch/dinner per day).
- As a user, I can assign an existing recipe to a planning slot.
- As a user, I can remove or replace a recipe in a slot.
- As a user, I can navigate between weeks (previous/next).

### Phase 3 — Shopping list
- As a user, I can generate a shopping list from the current week's meal plan.
- Ingredients shared across multiple recipes are aggregated (quantities summed, same unit).
- As a user, I can check off items as I shop.
- As a user, I can manually add items to the list that aren't from a recipe.
- As a user, I can flag an ingredient as "on sale this week" (price optional), and see recipes
  using it highlighted while planning (Direction B in §5, manual V1).

### Phase 4 — Pantry
- As a user, I can add/edit a stock item: name, quantity, unit, location
  (pantry/fridge/freezer), expiry date.
- As a user, I'm alerted about items close to expiry.
- The Phase 3 shopping list excludes or reduces quantities already available in stock.
- When a planned recipe is "cooked", the quantities used can be deducted from stock (to refine:
  automatic vs. manual confirmation).

## 7. Non-functional requirements

- **Responsive**: comfortably usable on mobile (shopping, browsing) and desktop (entering
  recipes).
- **Ease of use above all** — this is a daily-use tool, not a professional one: minimal friction
  to add a recipe or check off a grocery item.
- **Security**: proportionate to the use case (single shared account, no sensitive third-party
  data) — no need for robust multi-tenant architecture for now, but no hardcoded secrets in the
  code.
- **Hosting**: Google Cloud Run (see [03-tech-stack.md](03-tech-stack.md)).
- **Reasonable scalability**: the data model must be able to absorb Phase 4 (stock with
  quantities/expiry) and leave the door open for Phase 5 (AI) without a full rewrite — without
  over-engineering phases 1-3 for that.

## 8. Out of scope (for now)

- Multi-household / multi-tenancy (the app serves a single household).
- Fine-grained permissions between members of the same household.
- Native mobile app (targeting responsive web first).
- AI features (Phase 5): unspecified, not built before phases 1-4 are stable and actually used.

## 9. Next steps

1. ~~Validate/amend this document with the user.~~ Done.
2. ~~Detail the data model~~ — see [02-data-model.md](02-data-model.md).
3. ~~Choose the tech stack~~ — see [03-tech-stack.md](03-tech-stack.md).
4. Work through Phase 1 tasks — see [04-phase1-tasks.md](04-phase1-tasks.md).
