# v16 Engineering Audit — Shareable URL State

## Scope
Presentation/state-sharing only. Acquisition and analytical products remain unchanged from v15.

## Verified behavior
- State is serialized into a readable URL hash.
- Date, time, exhibitor, geography, observation mode, replay cutoff and 2–4 comparison cinemas can be restored.
- Shared historical dates load their day product before applying the remaining state.
- Invalid/stale values are ignored rather than causing a fatal render error.
- As-of replay remains backend-derived and hindsight-safe; the URL only selects an existing checkpoint.
- `Copy share link` copies the synchronized current URL, with a fallback instruction if clipboard permission is unavailable.

## Safety / semantics
No booking actions, seat holds, transactions, or paid-sales inference are introduced. Observed used/booked seat states retain the existing methodological caveats.
