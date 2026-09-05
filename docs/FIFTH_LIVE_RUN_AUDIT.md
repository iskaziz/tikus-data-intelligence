# Fifth Live Run Audit — v7 → v8

Live product reviewed: 2026-09-05, generated at 17:52:51 MYT.

## What v7 proved

Paragon `paragon-schedule/1.3.0` restored fresh read-only schedule observations and native `txtSessionId` values. Both tracked Paragon cinemas were represented again.

## Remaining analytical defects

1. Batu Pahat native session IDs `122652` (18:30) and `122653` (20:30) were neighbouring-film leakage and must remain in immutable history but be excluded from analytics.
2. KTCC 19:40 and 21:55 existed twice in the analytical product because legacy v1.1 fingerprint identities and v1.3 native identities referred to the same schedule-only screening.

## v8 resolution

- Adds a targeted correction ledger rule for Batu Pahat `122652` and `122653` on 2026-09-05 under `paragon-schedule/1.3.0`.
- Adds an analytical schedule-only identity reconciliation layer keyed by provider + cinema + show date + exact start time.
- When a native source session ID exists for the same schedule-only screening, it becomes canonical and legacy fingerprint observations are rewritten only in the analytical layer.
- Raw immutable history is never modified.
- Seat-measured observations are never reconciled by this rule.

## Validation against the supplied live product

Input analytical sessions: 77

Targeted exclusions: 2
- `paragon-batu-pahat:source:122652`
- `paragon-batu-pahat:source:122653`

Identity reconciliations: 2
- KTCC 19:40 fingerprint → `paragon-ktcc:source:83243`
- KTCC 21:55 fingerprint → `paragon-ktcc:source:83244`

Expected corrected analytical session count: 73.

Expected Paragon counts after v8 reconciliation:
- Paragon KTCC: 5
- Paragon Batu Pahat: 1

This audit does not reinterpret schedule-only observations as ticket sales or seat occupancy.
