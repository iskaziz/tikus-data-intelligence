# TIKUS! Data Intelligence v11 — as-of replay

v11 introduces hindsight-safe knowledge replay on top of v10. No collector or source contract changes.

## Product model

Each day product (`schemaVersion 1.6.0`) contains `asOfReplay`:

- `timezone`: Asia/Kuala_Lumpur
- `rule`: later observations are excluded
- `checkpoints`: fixed 12:00, 15:00, 18:00 and 21:00 MYT cutoffs when available

Each checkpoint contains:

- cutoff identity and timestamp;
- summary and cinema rankings;
- latest session state knowable by that time;
- session changes derived only from pre-cutoff history;
- Seat-State Momentum;
- Prime-Time Efficiency;
- session velocity leaders;
- observed allocation comparison;
- Decision Signals;
- explicit replay-quality metadata.

## Anti-hindsight rule

The checkpoint history is first filtered to `collectedAt <= asOf`. Every derived analytical layer is then recomputed from that restricted history. A later observation cannot influence an earlier replay even if it exists in repository history when the page is opened.

Intraday replay is methodologically partial, so Decision Signal confidence is capped at `low` and allocation comparison is marked limited.

## UI

Observation now supports:

- Latest observed (day)
- Live / upcoming
- Final pre-show (finalized only)
- As-of replay

Selecting As-of replay reveals a cutoff selector. The cinema table, KPI cards, momentum, prime-time efficiency, allocation and Decision Signals all switch to the selected backend-generated replay payload.

## Validation

- 34 unit tests pass.
- Dedicated tests prove later observations are excluded from earlier checkpoints.
- Dedicated tests prove intraday decision confidence stays low.
- End-to-end synthetic build produced 12:00/15:00/18:00 replay values from only the observations known at each cutoff.
- Python compilation passes.
- browser JavaScript syntax checks pass.
- semantic validator passes against retained repository data.

## Recommended next stage

After v11 collects through the end of a full day, add **session trajectory views**: per-session observed seat-state curves with fixed relative-to-showtime windows (for example T-6h, T-3h, T-1h and final pre-show), plus cinema-level rollups. Keep all trajectory language explicitly observational rather than ticket-sales based.
