# Fourth live-run audit — 5 September 2026, 00:39 MYT

Source examined: uploaded `current.json` generated at `2026-09-05T00:39:36+08:00`.

## Confirmed working

- Data product schema is `1.3.0`.
- Correction ledger is active and excludes the known defective Batu Pahat parser observations from analytics while retaining raw history.
- Final pre-show is correctly provisional: one started/finalized session and 71 future sessions at this observation time.
- GSC returned 42 seat-measured snapshots across all 8 tracked GSC cinemas.
- TGV returned 21 seat-measured snapshots across all 5 tracked TGV cinemas.
- Mega returned 4 schedule-only snapshots at Riverfront Mall.

## Remaining defect

Paragon collector v1.2 returned zero fresh snapshots across both tracked Paragon cinemas. The five KTCC rows visible in the analytical product were inherited from the earlier v1.1 observation. This means v1.2 fixed false positives by becoming too strict.

## v1.3 response

The v1.3 collector no longer depends on DOM ancestor relationships. It uses stable link semantics:

1. Identify movie-title anchors whose href contains `/Browsing/Movies/Details/`.
2. Select the exact title `TIKUS!`.
3. Define the film segment as everything after that title anchor up to the next movie-title anchor.
4. Read only `/Ticketing/visSelectTickets.aspx` anchors inside that segment.
5. Associate each ticketing anchor with the most recent explicit date heading.
6. Keep only anchors under the requested show date.
7. Preserve `txtSessionId` as the native source session ID.

The collector also emits per-cinema diagnostics in `collection.latestRun.sourceStatuses.paragon.diagnostics`, including title-anchor counts, TIKUS! anchor counts, ticket-anchor counts, parsed-session counts and rejection reasons.

## Decisive next-run checks

A successful v1.3 run should show:

- `collectorVersion: paragon-schedule/1.3.0` on new Paragon snapshots.
- `sourceSessionId` populated from `txtSessionId`.
- `collection.latestRun.sourceStatuses.paragon.diagnostics` populated for both cinemas.
- Fresh Paragon snapshots from Batu Pahat and KTCC when TIKUS! remains scheduled on the requested date.
- No reappearance of quarantined v1.0/v1.1 Batu Pahat false sessions in analytical products.
