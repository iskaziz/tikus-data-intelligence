# TIKUS! Data Intelligence v16 — Shareable URL State

v16 adds a client-side shareable URL/hash state for internal comparison workflows. No collector, correction, reconciliation, analytics, schema, or immutable history behavior changed.

## URL state

The hash can preserve:
- `date` — selected show date
- `time` — all / matinee / prime / late
- `exhibitor` — exhibitor filter
- `state` — geography filter
- `obs` — latest / live / final / asof
- `replay` — as-of replay checkpoint when applicable
- `compare` — 2–4 comma-separated cinema IDs

Example shape:
`#v=1&date=2026-09-05&time=prime&exhibitor=tgv&obs=asof&replay=1800&compare=tgv-wangsa-walk,tgv-bukit-tinggi`

Invalid/stale values are ignored safely. If a shared date differs from the bootstrap date, that day product is loaded before the remaining state is applied.

## UI

The Cinema Comparison Workspace now includes **Copy share link**. The current browser URL is continuously synchronized with the analytical scope and comparison selection using `history.replaceState`, so copying the address bar also works.

## QA

- 38/38 tests pass
- semantic validator passes
- Python compilation passes
- JavaScript syntax checks pass
- dedicated share-state surface regression test passes

## Next candidate

A lightweight internal briefing mode could consume the same URL state and open directly into a condensed comparison-only screen for mobile sharing or executive review.
