# v9 — Distribution Intelligence

## Scope

v9 leaves collectors and normalization unchanged and adds a derived analytics/presentation layer.

## Added analytical products

`intelligence.cinemaMomentum`
- qualifying repeated-measurement session count
- net latest used/booked-state delta
- average latest seats/hour
- max/min latest seats/hour

`intelligence.primeTimeEfficiency`
- prime show count
- measured prime sessions
- prime capacity / observed used
- prime occupancy
- all-day occupancy
- percentage-point occupancy delta

`intelligence.sessionVelocityLeaders`
- fastest positive latest observed seat-state velocities with session/cinema/timestamp context

`intelligence.allocationComparison`
- current vs previous observed show count by cinema
- current vs previous prime-time show count
- explicit `comparable` or `limited-partial-day` quality

## Dashboard

New panels:
- Seat-State Momentum
- Prime-Time Efficiency
- Observed Allocation Change

All language remains source-semantic and avoids implying ticket sales, admissions or box office.

## QA

- 28/28 unit tests passing
- semantic validator passing
- Python compileall passing
- JavaScript syntax checks passing
