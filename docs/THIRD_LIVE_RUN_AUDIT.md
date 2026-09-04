# TIKUS! Data Intelligence — Third Live Run Audit

Basis: September 5, 2026 dataset generated shortly after midnight.

## Confirmed pipeline progress

- 16/16 tracked cinemas observed.
- 76 TIKUS! sessions observed across the tracked network.
- 62 sessions have public seat-state measurements (81.6% coverage).
- GSC and TGV seat-state acquisition is operational.
- Paragon and Mega remain schedule-only by design.

## Correctness findings

1. Paragon Batu Pahat v1.1 still emitted schedule times inconsistent with the verified TIKUS! card. v6 replaces text-neighbourhood parsing with smallest-shared-ancestor HTML-tree extraction.
2. Known Batu Pahat observations created by parser versions 1.0/1.1 on September 4–5 are retained in immutable history but excluded from analytics through `data/meta/corrections.json`.
3. Final-pre-show metrics were previously populated for future sessions. v6 only finalizes a session after its start time has passed, using the last stored observation at or before showtime.
4. Daily final-pre-show state is explicit: `provisional`, `complete`, or `no-observations`.

## Interpretation

Seat-state fields remain observations, not paid ticket sales. GSC B-state and TGV `seatsused` retain their source-specific conservative labels.
