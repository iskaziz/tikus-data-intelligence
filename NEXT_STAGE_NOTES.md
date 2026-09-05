# v13 — Individual Screening Trajectory Explorer

## Goal
Expose the v12 backend trajectory checkpoints at the individual screening level inside each cinema detail.

## Implementation
- Screening selector lists only measured sessions available in the current scope.
- Four checkpoint cards: T−6h, T−3h, T−1h, Final pre-show.
- Each observed checkpoint displays used/capacity, observed occupancy, exact `collectedAt`, and `minutesBeforeShow`.
- Missing checkpoints explicitly remain unavailable; final pre-show stays unavailable before session start.
- Clicking or keyboard-activating a measured session row selects that trajectory.
- As-of replay uses its own backend `sessionTrajectories`, preventing hindsight leakage.

## Non-goals
- No sales inference.
- No interpolation between observations.
- No collector changes.
- No modification of immutable history.
