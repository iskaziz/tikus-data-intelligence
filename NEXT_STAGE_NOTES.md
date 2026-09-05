# TIKUS! Data Intelligence v17 — Condensed Briefing Mode

v17 adds a presentation-only condensed internal briefing mode on top of the v16 shareable URL state. No collector, correction, reconciliation, analytics, schema, or immutable history behavior changed.

## Briefing state

The hash now optionally preserves:
- `brief=1` — open directly in condensed briefing mode.

All existing v16 state remains supported:
- date
- time band
- exhibitor
- geography
- observation mode
- replay cutoff
- 2–4 comparison cinemas

A briefing link therefore restores the same analytical scope before rendering the condensed view.

## Briefing contents

The condensed view deliberately limits itself to the selected comparison cinemas and shows:
- selected cinema count
- observed show count
- seat-measured session count
- aggregate observed occupancy
- per-cinema shows, occupancy, Seat-State Performance Index, momentum, prime-time delta and Decision Signal/confidence
- T−6h / T−3h / T−1h / final-pre-show trajectory comparison
- Decision Signal evidence
- the repository seat-state caveat

The view uses the same already-generated comparison/intelligence objects as the full dashboard. It does not recalculate metrics with different semantics.

## Mobile / sharing

- `Briefing mode` enters the condensed view.
- `Copy briefing link` preserves the active scope plus `brief=1`.
- `Exit briefing` returns to the full dashboard without losing the selected scope.
- Responsive layout collapses comparison cards and controls for narrow screens.

## Methodological guardrails

- Observed used/booked states remain explicitly not confirmed paid ticket sales.
- As-of replay remains hindsight-safe because briefing mode consumes the active replay intelligence rather than current-day data.
- Schedule-only cinemas remain visibly non-seat-measured.
- No forecasting or automated allocation recommendation language is introduced.

## QA

- full unit suite passes, including dedicated briefing surface/hash regression
- semantic validator passes
- Python compilation passes
- JavaScript syntax checks pass
- direct briefing DOM/hash integrity check passes

## Next candidate

A compact executive trend summary could compare the selected cinemas across multiple completed theatrical days, while explicitly separating final-pre-show results from partial-day observations.
