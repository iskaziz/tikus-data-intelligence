# v7 — Paragon link-semantic recovery

This release changes only the Paragon acquisition path and collector diagnostics.

## Changes

- `paragon-schedule/1.3.0`
- Exact TIKUS! movie-title anchor required.
- Movie-title href must use `/Browsing/Movies/Details/`.
- Showtime href must use `/Ticketing/visSelectTickets.aspx`.
- Parsing stops at the next movie-title anchor.
- Explicit date headings scope ticketing anchors to the requested day.
- Native `txtSessionId` is preserved as `sourceSessionId` and drives stable session identity.
- Per-cinema Paragon parser diagnostics are embedded in the collection run status.
- Existing correction ledger is unchanged.
- GSC, TGV, Mega, analytics and presentation logic are intentionally unchanged.

## Validation

- 22 automated tests passing.
- Semantic repository validator passing.
- Python compilation passing.
- Browser JavaScript syntax check passing.

## Next validation

Commit v7 and manually run the collector. The decisive fields are under:

`collection.latestRun.sourceStatuses.paragon`

If Paragon still returns zero sessions, the new diagnostics should identify whether GitHub Actions saw no exact movie anchor, no ticket anchors inside the TIKUS! segment, or no ticket anchors under the requested date.
