# ForkCast — Backlog roadmap (simplest → most complex)

> Status: living document. Source ideas live in [01-requirements.md](01-requirements.md) §4/§5 —
> this file just orders them by how much work each one actually is, so there's always an obvious
> next pick instead of re-deciding from scratch every time. Re-order it as items ship or turn out
> to be harder/easier than expected; keep it in sync with `01-requirements.md` (bullet gets struck
> through there, item gets marked done here).

## How to use this

When there's no explicit task queued and the answer to "what's next" is "pick something from the
backlog", start at the top of the first tier with an unclaimed item. Move to the next tier once a
tier is empty. Every item should map back to a bullet in `01-requirements.md` §4/§5 — if it
doesn't yet, add it there first (existing project rule, see `AGENTS.md`).

## Tier 1 — Wiring/UI only, no new model, no external dependency (done, 2026-08-07)

1. ~~**Expose the new recipe metadata in the list/filters**~~ — done (PR #17):
   `meal_moment`/`cooking_mode`/`difficulty`/`estimated_cost` now filterable and shown as pills on
   `list.html`.
2. ~~**Diet/allergy filters**~~ — done: the tag filter on `list.html` is now a checkbox group
   (`RecipeListView.get_queryset` ANDs each selected tag via its own `.filter(tags__id=...)` call)
   instead of a single-select dropdown, so selecting "vegetarian" + "gluten-free" together requires
   both, not either.
3. ~~**Strengthen rotation/anti-repetition**~~ — done: `surprise_me` now excludes recipes already
   assigned to any `MealSlot` in the current ISO week before applying the existing
   `last_cooked_on` ordering, so it won't suggest a recipe already planned for another day this
   week. Manual assignment in the planning grid is untouched — deliberately excluding from the
   *suggestion* algorithm only, not blocking a user's own choice to repeat a recipe on purpose.

## Tier 2 — New cross-referencing logic, still pure Django/SQL, no external calls

4. ~~**Expiry notifications**~~ — done: a `role="alert"` banner at the top of the recipe list page
   lists `StockItem`s expiring within `EXPIRY_WARNING_DAYS` (or already expired), each paired with
   one recipe using that ingredient when one exists (`_expiring_stock_suggestions()` in
   `views.py`). Placed on the recipe list rather than the pantry page since that's where the user
   is actually deciding what to cook (Direction A of the bidirectional loop).
5. ~~**Leftover management**~~ — done: `/leftover/` lists every recipe using a chosen ingredient
   (`leftover_search` in `views.py`), and when a matching quantity+unit is given, drops recipes the
   leftover can't cover even one serving of and shows the feasible serving count for the rest.
   Entry point is a small secondary form on the recipe list (deliberately less prominent than the
   "Surprends-moi" card — this is a targeted variant of that feature, not the headline one).
6. ~~**Cost estimate for groceries**~~ — done: `Ingredient.reference_quantity` +
   `reference_price` ("$4.99 for 1000 g", matching how a price tag reads) rather than the single
   per-unit price field originally sketched here — a per-gram price would round to $0.00 at 2
   decimal places and be awkward to type in anyway. `Ingredient` is admin-managed already (no
   in-app form needed). `ShoppingListItem.estimated_cost` / `ShoppingList.estimated_total` skip
   items with no pricing or a unit that doesn't match the ingredient's own unit, so the total is
   always a lower bound, never a wrong guess.

## Tier 3 — External API integration, but a free/simple one

7. ~~**Barcode scan via Open Food Facts**~~ — done, in a deliberately split-off first stage:
   `/scan/` takes a **typed** barcode (no camera yet — see below), looks it up against Open Food
   Facts (stdlib `urllib.request`, no new dependency for one unauthenticated GET), and offers
   "add to pantry" / "add to shopping list" pre-filled with the product name and, when parseable, a
   quantity. Adding to the pantry does `Ingredient.objects.get_or_create(name=product_name, ...)`
   rather than requiring the user to match an existing `Ingredient` first — a scanned name won't
   usually match one exactly, and forcing a match would defeat the "quick scan and done" point.
   **Deliberately deferred, not forgotten**: (a) the actual camera-based live scanning UI (a JS
   barcode-reading library) — the typed-entry version proves out the OFF integration and pantry/
   list plumbing first, camera capture is an additive UI layer on top, not a prerequisite; (b)
   pulling macros/photo from Open Food Facts, which the original idea mentioned ("great for your
   whey") — `Ingredient` has no macro/photo fields today (`Recipe` does, but per-serving, a
   different concern), and adding them is a real modeling decision to make deliberately, not a side
   effect of wiring up a barcode lookup.
7b. **Camera-based barcode scanning** (fast-follow to #7, not started) — replace/augment the typed
   barcode field on `/scan/` with a live camera reader (e.g. `html5-qrcode` via CDN, matching the
   no-build-step approach already used for htmx/Alpine). All the lookup/pantry/list plumbing from
   #7 stays as-is; this only changes how the barcode gets typed in. Needs real-device testing
   (camera permissions, HTTPS requirement) that a Playwright pass can't fully substitute for.
8. **Recipe import from a URL** — most recipe sites embed `schema.org/Recipe` structured data
   (JSON-LD), so a first version can be a scraper that looks for that block rather than parsing
   arbitrary HTML — meaningfully simpler than a general-purpose scraper, and doesn't need an LLM.
   Falls back to "paste manually" for sites without structured data instead of trying to handle
   every case.

## Tier 4 — Multiple moving parts or a new domain model

9. **Long-process tracker** (sourdough, marinades, fermentation) — a genuinely new model
   (something like `LongProcess`: name, started_on, expected_ready_on, notes) plus its own small
   dashboard. Not hard individually, but it's a new concept in the domain model rather than an
   extension of an existing one, unlike tiers 1-3.
10. **"Meal prep" mode** (merge shared prep steps across the week's recipes) — needs `Step`/
    `RecipeIngredient` to carry enough structure to detect overlap (which ingredient, which action)
    rather than free text as today. The ingredient-level `state` field added in PR #16 is a start,
    but steps themselves are still a plain description string — this needs that structure decided
    first.
11. **Automatic weekly plan generation** — explicitly scoped in `01-requirements.md` as a capstone
    on top of Direction A V2 (pantry-aware suggestions) and Direction B V2 (automatic deals) once
    both exist; depends on tier 5 items below, so it can't move earlier regardless of its own
    difficulty.

## Tier 5 — Real AI/external-data uncertainty (Phase 5 proper)

12. **Automatically fetching store discounts/flyers** (Direction B V2) — scraping or an API like
    Flipp/Reebee, reliability unproven, one of the two ideas explicitly flagged in the requirements
    doc as "evaluate when the time comes."
13. **Photo-based product recognition for the pantry** — needs an image-recognition model/API.
14. **Receipt scanning/OCR** — needs a reliable OCR pipeline plus parsing loosely-structured
    receipt text into ingredient/quantity.
15. **Voice-driven pantry/list updates** (Gemini/Siri Shortcuts + backend LLM parsing) — several
    integration points across systems the user doesn't fully control (Google Tasks API quotas,
    Shortcuts reliability), plus the LLM-parsing endpoint itself.
16. **Recipe import from an Instagram/TikTok video** — needs video transcription/extraction before
    any parsing can even start; explicitly flagged in the requirements doc as closer to Phase 5 AI
    complexity than to the plain URL-import idea (#8).
