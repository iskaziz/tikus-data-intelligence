# TIKUS! Data Intelligence v12 — session trajectory intelligence

v12 adds comparable relative-to-showtime trajectory analytics without changing any source collector.

## Product model

Day product schema is `1.7.0`. `intelligence.sessionTrajectories` contains:

- standard windows: T−6h, T−3h, T−1h and Final pre-show;
- per-session trajectory records;
- per-cinema capacity-weighted rollups;
- explicit checkpoint/complete-trajectory counts;
- `occupancyLift6hToFinal` when both endpoints exist.

## Checkpoint rule

For a target checkpoint C, the system selects the latest valid seat-measured observation whose `collectedAt <= C`. It never chooses the nearest observation after the cutoff. Final pre-show remains unavailable until the screening has actually started.

This preserves the same anti-hindsight principle used by v11 as-of replay.

## Cinema rollup

Cinema checkpoint occupancy is:

`sum(observed used) / sum(observed capacity)`

across sessions with a known point at that checkpoint. It is not an arithmetic average of session occupancies.

## UI

The dashboard adds **Session Trajectories** with cinema-level T−6h / T−3h / T−1h / Final occupancy, T−6h→Final percentage-point lift and complete-curve coverage.

As-of replay switches the trajectory panel to the replay-specific backend product rather than current-day trajectory data.

## Validation

- 37/37 automated tests pass.
- T−6h anti-hindsight regression passes.
- Final pre-show availability regression passes.
- Capacity-weighted cinema rollup regression passes.
- Python compilation passes.
- Browser JavaScript syntax check passes.
- Semantic repository validator passes.

## Recommended next stage

Add a compact **individual screening trajectory explorer** inside cinema detail: select a show and inspect observed used/capacity plus collection timestamp at each relative checkpoint, followed by cross-day trajectory archetypes once multiple complete theatrical days exist.
