# Second live-run audit — 4 September 2026

Input: `current(10).json`, generated 2026-09-04 23:19:57 MYT.

## Confirmed working behaviour

- `liveUpcomingSessions` is 0 at 23:19 and the live summary is empty, so past sessions no longer masquerade as live inventory.
- Previously observed TGV sessions remain in the observed-day and final-pre-show products.
- TGV Tebrau has two observations, allowing a first valid seat-state velocity calculation (0 change over ~10.6 minutes).
- Latest-run diagnostics distinguish a successful source query with zero returned TIKUS! sessions from a source error.
- Daily completeness is correctly marked `partial` because collection started late in the theatrical day.

## Parser defect found

Paragon Batu Pahat was emitted as `00:30` on 4 September even though the official Batu Pahat TIKUS! schedule does not contain that screening. This is a movie-card scoping defect, not evidence of a real session.

The Paragon parser in v5 is now bounded to an exact TIKUS! movie-card candidate and stops at the next `Play Trailer` movie boundary. It also examines multiple exact-title occurrences and accepts only a candidate containing the requested date.

Collector version changes from `paragon-schedule/1.0.0` to `paragon-schedule/1.1.0`.

## Historical treatment

The false `paragon-batu-pahat:fingerprint:2026-09-04:00:30:unknown` observation already committed in historical data should not be silently deleted if immutability is being preserved. Mark it excluded/invalid in an explicit correction ledger, or rebuild analytical products with a known-bad-session exclusion list while keeping the source observation available for audit.

## Next operational test

Run the patched collector on 5 September from before the first screenings. The Paragon output should align with exact TIKUS! cards for Batu Pahat and KTCC, while GSC/TGV should provide repeated seat snapshots where their public sources expose them.
