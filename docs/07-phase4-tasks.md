# ForkCast — Phase 4: task breakdown

> Derived from [01-requirements.md](01-requirements.md) (Phase 4 user stories) and
> [02-data-model.md](02-data-model.md) (`StockItem`).
>
> Split into two PRs: pantry core first (this PR), then wiring it into the shopping list and the
> "mark as cooked" flow as a follow-up — those touch Phase 3 code and deserve their own review.

## Design choices

- **Lots, not running totals** — already decided in the data model doc: a `StockItem` is one
  purchased batch (its own quantity/unit/expiry), not a single row per ingredient. Two bags of
  rice bought at different times are two rows, because they expire at different times.
- **Expiry alert threshold**: items expiring within 3 days (inclusive) are flagged. Picked as a
  reasonable default, not derived from a requirement — easy to change if it doesn't feel right in
  practice.
- **Stock deduction on "cooked" is automatic, FIFO by expiry**: the data model doc explicitly left
  this open ("automatic vs. manual confirmation — decide when this phase is tackled"). Decision:
  automatic, deducting from the soonest-expiring lot(s) first per ingredient, best-effort (if
  stock is short, deduct what exists and don't error). Simpler UX than a confirmation step, and
  FIFO matches how a household would actually use up a pantry. Revisit if it proves surprising in
  practice.
- **Shopping list integration reduces auto quantities by what's in stock**, rather than removing
  the line item entirely, so the user still sees what a recipe calls for even when they have some
  on hand already partially covering it. A line disappears only when stock fully covers the need.

## Tasks — pantry core

- [x] T37 — `StockItem` model (ingredient FK, quantity, unit, location enum
      pantry/fridge/freezer, nullable expiry_date, added_on), admin.
- [x] T38 — Pantry page: list all stock items sorted by soonest expiry first (`nulls_last`), add/
      edit/delete a stock item.
- [x] T39 — Expiry alerts: `is_expiring_soon`/`is_expired` properties on the model, surfaced as
      `<mark>` badges ("Bientôt périmé" / "Périmé") on the pantry page.
- [x] T40 — Nav link to the pantry page.
- [x] T41 — Automated tests: CRUD (add/edit/delete), expiry boundary (no date, exactly at the
      3-day threshold, one day past it, already expired), sort order with nulls last, badge
      rendered on the page. 6 new tests (31 total). Also spot-checked visually: added a
      near-expiry item, confirmed the "Bientôt périmé" badge renders.

## Tasks — integration (follow-up PR)

- [ ] T42 — Shopping list generation subtracts available stock (same ingredient + unit) from the
      aggregated auto quantity; drop the line only if stock fully covers it.
- [ ] T43 — "I cooked this" also deducts the recipe's ingredients from stock, FIFO by expiry,
      best-effort.
- [ ] T44 — Automated tests for both.

## Out of scope

Photo-based pantry input, receipt OCR (Phase 5 backlog, unchanged).
