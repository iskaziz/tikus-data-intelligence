# Eleventh engineering audit — cinema comparison workspace

## Scope
v14 adds a client-side cinema comparison workspace. Acquisition, correction/reconciliation, analytics generation and historical storage are unchanged from v13.

## Comparison semantics
The workspace compares 2–4 cinemas inside the active dashboard scope. It consumes existing backend-derived objects rather than defining parallel formulas in JavaScript.

Compared fields include:
- observed show allocation and prime-time show allocation
- observed capacity and used/booked state
- capacity-weighted occupancy
- Seat-State Performance Index
- repeated-observation Seat-State Momentum
- prime-time occupancy delta versus all-day occupancy
- T−6h, T−3h, T−1h and final pre-show cinema trajectory checkpoints
- trajectory completeness
- observed allocation delta versus the prior available theatrical day
- Decision Signal and confidence

The workspace inherits date, time, exhibitor, geography, observation mode and as-of replay. It therefore remains subject to the same completeness and no-hindsight rules as the surrounding dashboard.

## Selection behavior
Two cinemas are auto-seeded from the strongest currently measured rows by observed used/booked state, then occupancy. The user can replace those choices and add up to two additional cinemas. Duplicate selections are disabled.

## Safety and interpretation
“Used / Booked” remains an observed source-defined seat state and is not presented as paid ticket sales. Comparison does not generate forecasts or automatic exhibitor programming recommendations.

## Validation
- 37/37 repository tests pass.
- Semantic data validator passes.
- Python compilation passes.
- JavaScript syntax checks pass.
- Interface ID integrity check passes for all direct ID selectors used by the comparison workspace and dashboard controls.
