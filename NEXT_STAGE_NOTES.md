# TIKUS! Data Intelligence v10 — decision intelligence

v10 adds a conservative operational decision layer on top of v9. Collectors and acquisition semantics are unchanged.

## New product fields

`intelligence.decisionSignals` contains:

- `status`
- `quality`
- `networkOccupancy`
- `counts`
- per-cinema signals with evidence and confidence
- an explicit methodology definition/disclaimer

## Signal logic

A cinema is only promoted to **Review opportunity** when at least two independent positive indicators align and no cautionary indicator conflicts. Multiple negative relative indicators become **Capacity watch**. Conflicting evidence becomes **Mixed signal**. Everything else remains **Monitor**.

Evidence can include Seat-State Performance Index, repeated-measurement seat-state momentum, prime-time occupancy delta and comparable observed allocation change.

Daily completeness is part of confidence. Partial acquisition always yields low confidence.

## UI

A new **Decision Signals** panel presents signal counts and an evidence table. It remains analytical and compact; no maps, alerts or decorative scoring gauges were added.

## Validation

- 31 unit tests pass.
- semantic validator passes.
- Python compilation passes.
- browser JavaScript syntax checks pass.
- browser-facing schema supports `1.5.0`.

## Recommended next stage

After at least one complete full theatrical day under v10, add an **as-of replay** so the producer can inspect what the decision panel would have shown at different collection times (for example 12:00, 15:00, 18:00 and final pre-show) without hindsight leakage.
