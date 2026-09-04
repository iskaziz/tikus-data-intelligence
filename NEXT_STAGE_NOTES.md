# TIKUS! Data Intelligence — v6 correctness pass

## Implemented

- Paragon schedule parser v1.2.0 uses HTML-tree/card containment instead of unbounded text neighbourhoods.
- Added `data/meta/corrections.json`; proven collector defects are excluded from analytics while immutable history remains untouched.
- Quarantines Batu Pahat observations from Paragon parser v1.0/v1.1 on 2026-09-04 and 2026-09-05.
- Final-pre-show observations are finalized only after session start time has passed.
- Added `finalPreShowState` (`provisional`, `complete`, `no-observations`) with started/future/finalized counts.
- Dashboard final-pre-show mode explicitly says “finalized only”.
- Dashboard quality note surfaces corrected-observation exclusions.
- Day trend uses final-pre-show figures only when the day product marks them complete.
- Added third live-run audit and product-correctness tests.

## Next operational check

Run the collector after committing v6. A healthy September 5 result should no longer contain Batu Pahat observations created by `paragon-schedule/1.1.0` in analytical arrays, and new Paragon observations should report `paragon-schedule/1.2.0`.
