# Ninth live-run engineering audit — v12 trajectory layer

## Scope

v12 is an analytics-only release. GSC, TGV, Paragon and Mega acquisition contracts are unchanged.

## Why trajectories are useful

Absolute latest occupancy mixes screenings that are many hours apart in their booking/seat-state lifecycle. Relative checkpoints make screenings more comparable by asking what was observable at equivalent distances from showtime.

## Methodological safeguards

1. A checkpoint can only use a measurement collected at or before its cutoff.
2. No later measurement is interpolated backward.
3. Final pre-show is only knowable after the screening start time has passed.
4. Missing checkpoints remain missing rather than becoming zero.
5. Cinema rollups are capacity-weighted.
6. Every metric remains an observed seat-state metric, not paid ticket sales, admissions or box office.
7. As-of replay recomputes trajectories from its knowledge-restricted history.

## Standard windows

- T−6h
- T−3h
- T−1h
- Final pre-show

The source's hourly collection cadence means a checkpoint observation may be earlier than the exact target time. The product stores the actual `collectedAt` and `minutesBeforeShow` for audit.

## Validation

37 automated tests pass, including dedicated anti-hindsight and capacity-weighting trajectory tests. Repository semantic validation and JavaScript syntax validation also pass.
