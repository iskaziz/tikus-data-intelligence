# TIKUS! Data Intelligence — Methodology

## 1. What this repository measures

TIKUS! Data Intelligence records publicly observable theatrical scheduling and seat-state information for the producer-confirmed 16-cinema tracked network.

The atomic fact is **one observation of one screening at one collection time**.

Session identity prioritises the exhibitor's native session ID when one is publicly exposed. Only when a native ID is unavailable does the repository create a deterministic fingerprint from cinema, date, start time and auditorium. This keeps repeated observations of the same screening on one history line.

A session and an observation are different things. A screening at 20:00 can be observed repeatedly during the day; those observations form a time series for the same session.

## 2. What it does not claim to measure

The project does **not** claim access to:

- confirmed paid ticket sales;
- admissions;
- gross or net box office;
- distributor revenue;
- average ticket price derived from actual transactions;
- Malaysia-wide film market share;
- competitor-film performance;
- audience demographics.

No such values may be fabricated, estimated from seat state, or presented as if authoritative.

## 3. Source semantics

### GSC

Observed public seat-map states are normalized as follows:

- `A` → available;
- `B` → booked-state;
- any other observed status → `otherUnavailable` and retained in `statusCounts`.

For a measured session:

```text
capacity = A + B + all other observed seat states
used = B
available = A
otherUnavailable = sum(all states except A and B)
occupancy = used / capacity
```

`B` must never be labelled confirmed paid ticket sales. Public booking systems can contain temporary locks or other booking-state behaviour, so the safe language is **Observed Used / Booked** or **Booked-State Seats**.

### TGV

The established public API exposes:

- `seatstotal` → observed allocated seat capacity;
- `seatsused` → observed used/unavailable inventory;
- `usedpercentage` → source-provided percentage where present.

The normalized calculations are:

```text
capacity = seatstotal
used = seatsused
available = seatstotal - seatsused
occupancy = seatsused / seatstotal
```

`seatsused` may include held or otherwise unavailable inventory and must not be called confirmed paid sales.

### Paragon

Public schedules and booking-session identifiers can be observed. Seat counts are not treated as publicly available unless a future read-only source exposes them clearly without seat selection or temporary holds.

Until then:

```text
capacity = null
used = null
available = null
occupancy = null
measurementStatus = schedule-only
```

### Mega Cineplex

The currently established source is scheduling-oriented. No seat count is invented when unavailable.

## 4. Missing data

**Unknown is not zero.**

`null` means the measurement is unavailable or not eligible. Zero means a valid observation produced the value zero.

For this reason Paragon and Mega sessions can contribute to show-allocation metrics while being excluded from seat-weighted metrics.

## 5. Time bands

The repository uses non-overlapping local-time bands in `Asia/Kuala_Lumpur`:

- Matinee: before 18:00;
- Prime Time: 18:00 inclusive to 21:00 exclusive;
- Late: 21:00 onward;
- All Day: no time-band restriction.

The boundaries live in `data/meta/methodology.json`, not in presentation code.

## 6. Headline calculations

Let `M` be the set of seat-measured sessions inside the current analytical scope.

### Total Shows

Number of distinct session identities in scope.

### Locations with Confirmed Shows

Number of distinct cinemas containing at least one observed TIKUS! session in scope.

### Observed Capacity

```text
Σ capacity(s), for s in M
```

### Observed Used / Booked

```text
Σ used(s), for s in M
```

### Occupancy

The headline is capacity-weighted:

```text
Σ used / Σ capacity
```

Do not calculate the headline as an unweighted average of individual session percentages.

### Average Used per Measured Session

```text
Σ used / count(M)
```

### Average Allocated Seats per Measured Session

```text
Σ capacity / count(M)
```

### Seat Coverage

```text
seat-measured sessions / total sessions
```

Coverage should be displayed with the seat metrics rather than hidden in a footnote.

## 7. Shares

Shares are always relative to the active **scope**, not a hidden national denominator.

### Show Share

```text
cinema shows / shows in active scope
```

### Seat Share

```text
cinema observed capacity / observed capacity in active seat-measured scope
```

Search, sorting and column visibility are presentation controls and must not silently redefine these denominators.

## 8. Seat-State Performance Index

For cinema `i`:

```text
PI_i = (used_i / used_scope) / (capacity_i / capacity_scope)
```

When the numerator and denominator use identical session eligibility this is equivalent to:

```text
PI_i = occupancy_i / occupancy_scope
```

Interpretation:

- `1.00×` → proportional to its observed capacity allocation;
- `>1.00×` → higher observed-used share than capacity share;
- `<1.00×` → lower observed-used share than capacity share.

The preferred label is **Seat-State Performance Index**, not Sales Performance Index.

The index is `null` when there is no eligible measured capacity, no scope used value, or incompatible/missing seat observations.

## 9. Historical snapshots and velocity

Normalized snapshots are append-only.

For two observations of the same session:

```text
used_delta = used(t2) - used(t1)
velocity = used_delta / elapsed_hours
```

The metric is **Net Seat-State Velocity**, expressed as observed seats per hour. It is not tickets per hour.

Negative velocity is valid and can reflect released holds, changed unavailability, corrections or other source behaviour.

## 10. Daily comparisons

Daily products should eventually expose both:

- **Live/latest**: latest valid observation currently available;
- **Final pre-show**: last valid observation before each session begins.

Opening Day, Day 2 and subsequent-day comparisons must use the release date as the day-of-run anchor and preserve data coverage.

## 11. Allocation changes

A session absent from one collector run is not automatically called cancelled.

Recommended states:

- first seen;
- still scheduled;
- new since previous observation;
- previously seen / currently missing;
- confirmed removed only when the source evidence and repeated successful scans justify that classification.

## 12. Safety and non-interference

Collectors are read-only. They must not:

- select seats;
- create temporary seat holds;
- submit bookings;
- enter payment flows;
- infer occupancy from actions that themselves modify availability.


## Correction ledger

Analytical products may exclude observations through `data/meta/corrections.json` when a collector defect is proven. Raw history is never rewritten or deleted. Each exclusion remains attributable to a correction ID and reason.

A **final pre-show** observation is only finalized after the session start time has passed, because only then can the system know which stored pre-start observation was the last one. Future sessions remain provisional and are excluded from final-pre-show metrics.

## 13. Distribution-intelligence layer

v9 adds derived distribution intelligence while preserving the source semantics above.

### Seat-State Momentum

For each session with at least two valid seat measurements, the latest two observations produce:

```text
latest_used_delta = used(t2) - used(t1)
latest_velocity = latest_used_delta / elapsed_hours
```

Cinema momentum aggregates only these qualifying repeated observations. `netUsedDelta` is the sum of latest session deltas and `averageSeatsPerHour` is the arithmetic mean of qualifying session velocities. It is an **observed seat-state signal**, not ticket-sales momentum.

### Prime-Time Efficiency

Prime time remains 18:00 inclusive to 21:00 exclusive. Prime-time occupancy is capacity-weighted:

```text
prime_occupancy = sum(prime_used) / sum(prime_capacity)
```

`occupancyDelta` is prime-time occupancy minus that cinema's all-day observed occupancy. It is shown as a percentage-point difference, not a sales uplift.

### Observed Allocation Change

The day comparison uses distinct repository-observed sessions by cinema and compares show count and prime-time show count with the previous available theatrical day.

If either day's acquisition is partial, the comparison quality is `limited-partial-day`. In that state, differences are descriptive of observed repository coverage and must **not** be presented as definitive exhibitor programming changes.

## As-of replay

As-of replay is a knowledge-time reconstruction. For a checkpoint at time **T**, only observations whose `collectedAt <= T` are eligible. All session state and derived analytics are recomputed after that restriction; later observations are never back-propagated into an earlier checkpoint.

Standard replay checkpoints are 12:00, 15:00, 18:00 and 21:00 Asia/Kuala_Lumpur when available. Intraday replay is always treated as partial-day evidence. Decision-signal confidence is capped at low and allocation deltas remain limited. Final pre-show is a separate session-relative measure and must not be conflated with a wall-clock replay.
