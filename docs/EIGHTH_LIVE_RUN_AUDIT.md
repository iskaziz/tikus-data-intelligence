# Eighth live-run / v11 audit — hindsight-safe replay

## Trigger

By the 5 September 17:52 MYT product, the repository had accumulated repeated observations across the theatrical day and 46 finalized pre-show sessions. This made historical operational replay useful: a producer should be able to inspect what the system knew at noon or mid-afternoon without later observations changing the answer.

## Risk addressed

A naive historical UI can leak hindsight by taking the current latest session state and merely relabelling it with an earlier clock time. That would make earlier rankings, momentum and decision signals invalid.

## v11 control

For each replay cutoff, v11 filters analytical history to observations with `collectedAt <= cutoff` before deriving any metric. It then recomputes:

- current session state;
- cinema rankings;
- repeated-measurement momentum;
- prime-time efficiency;
- session velocity;
- allocation comparison;
- Decision Signals.

Later observations are not available to the checkpoint code path.

## Checkpoints

Standard local cutoffs are 12:00, 15:00, 18:00 and 21:00 Asia/Kuala_Lumpur. For the current theatrical date, only cutoffs that have already passed are emitted. Past dates expose all standard cutoffs for which stored observations exist.

Final pre-show remains separate because it is session-relative rather than a single wall-clock knowledge cutoff.

## Quality semantics

All intraday replay checkpoints are partial-day evidence. Decision Signal confidence is therefore capped at low, and allocation comparison cannot be upgraded to a definitive programming-change interpretation.

## Validation

A regression test creates observations at 11:00 and 13:00, then reconstructs 12:00. The replay correctly returns the 11:00 state and explicitly declares that later observations were not used. An end-to-end synthetic day build produced distinct 12:00, 15:00 and 18:00 states from the appropriate historical subsets.
