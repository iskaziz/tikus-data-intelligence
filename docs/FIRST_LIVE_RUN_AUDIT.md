# First live-run audit — 2026-09-04 22:58 MYT

Source: user-provided `current.json` generated at `2026-09-04T22:58:33+08:00`.

## What worked

- The pipeline successfully produced a valid `current.json` with schema, summaries, session-level facts, cinema rankings, exhibitor summaries, state summaries, history series and source semantics.
- TGV returned two seat-measured sessions:
  - TGV Bukit Tinggi — 23:00 — capacity 115 — `seatsused` 1.
  - TGV Tebrau City — 23:15 — capacity 76 — `seatsused` 0.
- Aggregate TGV seat state was therefore 1 / 191, or 0.52% observed occupancy. This is an observed seat-state metric, not ticket sales.
- Paragon Batu Pahat was retained schedule-only with no invented seat data.

## Problems exposed

1. Only 3 of the 16 tracked cinemas appeared in the day product.
2. The first collection was extremely late in the theatrical day. Sources that return only current/upcoming inventory cannot reconstruct earlier sessions from a 22:58 first observation.
3. Paragon Batu Pahat's 00:30 session was first observed at 22:58, long after showtime. It is legitimate evidence that the official page still exposed that schedule, but it should not appear as a live/upcoming session.
4. `current.json` did not contain enough source-run diagnostic information to tell, from that file alone, whether GSC/Mega returned zero sessions normally or failed during acquisition.

## v4 correction

- Adds `liveSessions` and `liveSummary` for same-day sessions that have not started at product-generation time.
- Retains full observed-day sessions separately for audit/history.
- Adds `collection.firstSeenAfterShowSessionIds` and count.
- Marks daily completeness as partial when the evidence itself demonstrates late discovery.
- Embeds the latest collector-run metadata into each day/current product.
- Collector source status now includes observed cinema IDs and expected tracked-cinema count.
- Dashboard gains a `Live / upcoming` observation mode and surfaces first-seen-after-show warnings.

## Interpretation rule

A missing cinema after a late collector start is **not automatically a failed allocation** and **not automatically a collector error**. It can mean:

- the exhibitor exposes only upcoming inventory and the cinema's final TIKUS! show had already started;
- there was no TIKUS! session on that theatrical date;
- the source returned no matching session;
- or acquisition failed.

The enriched source status in v4 is intended to distinguish these states on subsequent runs.
