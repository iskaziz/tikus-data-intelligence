# Sixth Live-Run Audit — 5 September 2026, 17:52 MYT

Source reviewed: uploaded `current(20260905-095553).json` generated at 17:52:51 MYT.

## What the run established

- The repository observed all 16 tracked cinema locations.
- 77 analytical sessions were present before the v8 identity/correction reconciliation was applied to a new generated product.
- 63 sessions had seat-state measurements; Paragon and Mega remained schedule-only.
- 46 sessions had finalized pre-show observations and 30 remained future/upcoming at generation time.
- The final-pre-show state remained correctly `provisional`.

## Paragon finding carried into v8

The live product contained a genuine Batu Pahat 00:30 native session plus two known false native sessions, and duplicate KTCC identities from legacy fingerprints alongside newer native IDs. v8 corrects these analytically without mutating raw history, yielding 73 distinct analytical sessions when applied to this live set.

## v9 implication

This run is the first suitable basis for higher-level distribution signals because repeated GSC/TGV observations now exist through the day. v9 therefore introduces seat-state momentum, prime-time efficiency, session velocity leaders and guarded day-over-day allocation comparison. These remain observation-derived signals and are not box-office or paid-ticket metrics.
