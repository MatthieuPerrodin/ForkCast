# ForkCast — Data model

> Status: Phase 1 entities implemented and migrated (see `recipes/models.py`). Phases 2-4 entities
> below remain conceptual, derived from [01-requirements.md](01-requirements.md).

## 1. Design principles

- **One household, one shared account** (see requirements §3) → no need to scope every table by
  user/tenant. Simplifies the whole model.
- **Ingredient = a reusable reference table**, not a plain text field on each recipe. That's what
  makes it possible to: aggregate the shopping list, cross-reference recipes ↔ stock (headline
  feature), and sort by store aisle (backlog idea).
- **The pantry is modeled as "lots"** (`StockItem`) rather than one running total per ingredient: a
  bag of rice bought today and another bought 2 months ago have different expiry dates. Needed for
  expiry alerts (Phase 4 requirement).
- **No dedicated table for "meal suggestion"**: it's a query/algorithm computed on the fly from
  `Recipe` + `RecipeIngredient` + `StockItem` + `Tag` (+ `Deal` for Direction B), not stored data.
  Avoids complicating the model for a feature that's fundamentally a computation.
- **The meal ↔ grocery loop is bidirectional** (see requirements §5): `StockItem` serves Direction
  A ("I have this, what do I cook"), `Deal` serves Direction B ("what do I buy and cook this
  week"). Both plug into the same `Recipe`/`Ingredient`.

## 2. Entity-relationship diagram (overview)

```mermaid
erDiagram
    INGREDIENT ||--o{ RECIPE_INGREDIENT : "used in"
    RECIPE ||--o{ RECIPE_INGREDIENT : "needs"
    RECIPE ||--o{ STEP : "breaks down into"
    RECIPE ||--o{ RECIPE_TAG : "carries"
    TAG ||--o{ RECIPE_TAG : "applied to"
    RECIPE ||--o{ MEAL_SLOT : "planned for"
    INGREDIENT ||--o{ STOCK_ITEM : "stored as lots"
    INGREDIENT ||--o{ SHOPPING_LIST_ITEM : "appears on"
    SHOPPING_LIST ||--o{ SHOPPING_LIST_ITEM : "contains"
    INGREDIENT ||--o{ DEAL : "on sale"
```

## 3. Entities — Phase 1: Recipes (implemented)

### `Recipe`
| Field | Type | Notes |
|---|---|---|
| id | id | |
| title | text | |
| description | text | optional |
| photo | image/url | optional |
| prep_time_min | integer | used by the "quick" filter |
| cook_time_min | integer | optional |
| rest_time_min | integer | optional — dough resting, marinating, chilling... separate from active cook time |
| default_servings | integer | basis for quantity adjustment |
| nutrition_score | enum (light/balanced/hearty) or similar | intentionally simple, no calorie calculation (see backlog idea) |
| calories_kcal | integer, optional | per serving |
| protein_g / carbs_g / fat_g | decimal, optional | per serving — added for PPL/fitness routine tracking, separate concern from `nutrition_score` above (see §5) |
| fridge_shelf_life_days | integer, optional | how many days it keeps in the fridge once cooked |
| is_freezable | boolean | |
| seasonality_months | text, optional | comma-separated month numbers (e.g. "6,7,8") — see §5 for why not a proper array field |
| equipment_needed | text, optional | free text (e.g. "mixer, food processor") — see §5 for why not a structured list |
| estimated_cost | enum (low/medium/high), optional | |
| difficulty | enum (easy/medium/hard), optional | |
| cooking_mode | enum (oven/stovetop/no_cook/bbq), optional | |
| meal_moment | enum (breakfast/lunch/dinner/snack), optional | |
| last_cooked_on | date | nullable — feeds the suggestion's anti-repetition logic |
| created_at | datetime | |

### `Step`
| Field | Type | Notes |
|---|---|---|
| id | id | |
| recipe_id | FK → Recipe | |
| order | integer | |
| description | text | |

### `Ingredient` (reference table)
| Field | Type | Notes |
|---|---|---|
| id | id | |
| name | text | unique |
| default_unit | text | g, ml, piece... |
| aisle_category | enum | produce, pantry, frozen, dairy, meat & fish, beverages, other — used to sort the shopping list (backlog idea) |

### `RecipeIngredient` (join table)
| Field | Type | Notes |
|---|---|---|
| id | id | |
| recipe_id | FK → Recipe | |
| ingredient_id | FK → Ingredient | |
| quantity | decimal | for `default_servings` |
| unit | text | may differ from the ingredient's default unit (conversion — see §5 open questions) |
| state | text, optional | free text prep state at the ingredient level (e.g. "chopped", "melted", "room temperature") — distinct from `cooking_mode`/`meal_moment` above, which describe the recipe as a whole |

### `Tag` / recipe-tag relationship
| Field | Type | Notes |
|---|---|---|
| Tag.id, Tag.name | | e.g. "quick", "vegetarian", "gluten-free", "balanced" |
| Recipe.tags | M2M | plain Django `ManyToManyField`, no separate join model needed (no extra data on the relationship) |

## 4. Entities — Phases 2 to 4 (conceptual, not yet implemented)

### `MealSlot` (Phase 2 — Meal planning)
| Field | Type | Notes |
|---|---|---|
| id | id | |
| date | date | |
| meal_time | enum (lunch/dinner) | |
| recipe_id | FK → Recipe, nullable | empty = unplanned slot |
| planned_servings | integer | |

### `ShoppingList` / `ShoppingListItem` (Phase 3)
| Field | Type | Notes |
|---|---|---|
| ShoppingList.id, created_at | | one active list at a time, generally tied to a planning week |
| ShoppingListItem.id | id | |
| ShoppingListItem.shopping_list_id | FK → ShoppingList | |
| ShoppingListItem.ingredient_id | FK → Ingredient, nullable | nullable for "not from a recipe" additions |
| ShoppingListItem.free_text_name | text, nullable | used when there's no ingredient_id (manually added item) |
| ShoppingListItem.quantity / unit | | result of aggregating the planned recipes |
| ShoppingListItem.checked | boolean | |
| ShoppingListItem.source | enum (auto/manual) | |

### `StockItem` (Phase 4 — Pantry)
| Field | Type | Notes |
|---|---|---|
| id | id | |
| ingredient_id | FK → Ingredient | |
| quantity / unit | | |
| location | enum (pantry/fridge/freezer) | |
| expiry_date | date, nullable | feeds expiry alerts |
| added_on | date | |

### `Deal` (Direction B — manual V1 from Phase 3, automated in Phase 5)
| Field | Type | Notes |
|---|---|---|
| id | id | |
| ingredient_id | FK → Ingredient | |
| store | text, optional | e.g. "IGA", "Metro" — only useful if tracking multiple chains |
| sale_price | decimal, optional | |
| start_date / end_date | date | how long the deal is valid |
| source | enum (manual/flyer_import) | `manual` for V1; `flyer_import` reserved for future automation (Phase 5) |

## 5. Open questions / decisions for later

- **Unit conversion** (e.g. a recipe in "tablespoons", stock in "grams"): unresolved at this
  stage. For the MVP, an approximate manually-entered match is acceptable rather than a generic
  conversion engine.
- **Number of active shopping lists**: one at a time to start (simpler), to revisit if the need
  for parallel lists shows up in actual use.
- **Automatic stock deduction when a recipe is "cooked"** (mentioned in requirements §6 Phase 4):
  to decide between automatic and manual confirmation once that phase is actually tackled.
- **Nutrition score**: intentionally left as a simple enum (light/balanced/hearty) rather than a
  real macro calculation — to refine only if the need shows up in actual use.
- **Macros alongside the nutrition score, not replacing it** (added 2026-08-06): `nutrition_score`
  stays a quick, low-friction qualitative tag for everyday meal suggestions; `calories_kcal`/
  `protein_g`/`carbs_g`/`fat_g` are a separate, optional, more precise set of fields for recipes
  where exact macros actually matter (e.g. tracking a lifting/PPL routine). Both coexist rather
  than one replacing the other — different use cases, different precision needs.
- **`seasonality_months` as a comma-separated string, not a proper array/M2M**: SQLite (used
  locally) has no native array type, and a full M2M table for 12 fixed values is more structure
  than the feature needs. A `CharField` storing digits like `"6,7,8"` is simple to write/read from
  both SQLite and Postgres and easy to migrate to something richer later if it ever needs to be
  queried efficiently (e.g. "find all recipes in season this month").
- **`equipment_needed` as free text, not a structured equipment table**: same reasoning as
  `Ingredient.default_unit` elsewhere in this model — a full reference table would only pay off if
  the app needed to filter/aggregate by equipment, which isn't a requirement today.
- **"Style" tags (quick/meal-prep) reuse the existing `Tag` M2M, no new field**: the requirement
  that motivated this ("classification tags for style") is already served by tags like `#rapide` —
  adding a second, overlapping classification mechanism would just create two ways to say the same
  thing. `estimated_cost` and `difficulty` get dedicated enum fields instead of tags because they're
  closed, mutually-exclusive value sets (more like `nutrition_score` than like free-form tags).
- **`cooking_mode` and `meal_moment` are single-select enums on `Recipe`, not M2M**: a recipe could
  arguably fit more than one (e.g. suitable for lunch or dinner), but `nutrition_score` already
  established the "one simple enum per recipe" pattern for this kind of classification, and neither
  field is required — leave both blank rather than force a choice when it doesn't apply.
- **`RecipeIngredient.state` is free text, not an enum**: prep states ("chopped", "melted", "room
  temperature", "thinly sliced"...) are far more open-ended per-ingredient than the recipe-level
  enums above; an enum would either need constant editing or a large catch-all list. Revisit only
  if the "meal prep" backlog idea (merging shared prep steps across recipes) needs to match on
  state programmatically rather than just display it.

## 6. Next steps

1. ~~Validate this model with the user.~~ Done.
2. ~~Choose the tech stack.~~ Done — see [03-tech-stack.md](03-tech-stack.md).
3. Translate the Phase 2-4 entities above into actual migrations once those phases are tackled
   (Phase 1's `Recipe`/`Step`/`Ingredient`/`RecipeIngredient`/`Tag` are already implemented).
