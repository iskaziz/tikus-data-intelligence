# v8 — Paragon identity reconciliation

v8 is a correctness-only analytical patch based on the 2026-09-05 17:52 MYT live product.

## Changes

- Added targeted quarantine for Paragon Batu Pahat native session IDs `122652` and `122653` from collector `paragon-schedule/1.3.0` on 2026-09-05.
- Added `reconcile_schedule_only_session_ids()` in `scripts/analytics/build_products.py`.
- Reconciliation applies only to schedule-only observations sharing provider + cinema + show date + exact start time.
- Native source session IDs are preferred over legacy time fingerprints.
- Raw immutable history remains unchanged.
- Seat-measured GSC/TGV observations are never rewritten.
- Day/current products now expose reconciliation audit metadata under `quality.reconciledSessions`.

## Live-product regression result

The supplied v7 current product contains 77 analytical sessions. v8 produces 73 after exactly two targeted exclusions and two KTCC identity merges.

## QA

25 automated tests pass, including targeted correction and identity-reconciliation regression tests.
