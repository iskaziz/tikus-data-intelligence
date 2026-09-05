# TIKUS! Data Intelligence

A data-first theatrical-distribution intelligence repository for the Malaysian feature film **TIKUS!**.

This project is deliberately separate from the TIKUS! film microsite and the earlier cinema tracker UI. Its purpose is to preserve auditable public observations of theatrical allocation and seat state, then derive cinema-, exhibitor-, geography-, session- and time-based analytics without claiming access to paid ticket sales, admissions or box office revenue.

## Principles

- **Session snapshots are the atomic fact.** One record represents one observation of one screening at one collection time.
- **Unknown is not zero.** Missing seat data is stored as `null` and excluded from seat-weighted calculations.
- **Observed seat state is not ticket sales.** GSC `B` and TGV `seatsused` are never labelled confirmed sales.
- **Raw acquisition, normalization, analytics and presentation stay separate.**
- **History is immutable.** Normalized historical observations are append-only.
- **Canonical cinema names are controlled by this repository.** Source aliases never replace producer-confirmed display names.

## Tracked network

16 confirmed locations: 8 GSC, 5 TGV, 2 Paragon and 1 Mega Cineplex. The canonical registry is in `data/meta/cinemas.json`.

## Current implementation

### Live acquisition

- GSC schedule discovery via its read-only public XML showtime endpoint.
- GSC seat-state observation via the read-only public hall-seat-status XML endpoint.
- TGV schedule discovery via the official `moviesession_get` API.
- TGV seat-state observation via the official `moviesession_getseatstatus` API.
- Paragon and Mega remain explicitly **schedule-only / no inferred seat counts** until a stable read-only schedule adapter is established for the new repository.
- No collector selects seats, opens an order, creates a temporary hold or enters payment.

### History and analytics

- append-only normalized history under `data/history/YYYY-MM-DD/`;
- per-run audit manifests under `data/runs/`;
- browser-facing `data/current.json`;
- per-day products under `data/days/`;
- compact per-session time series and latest seat-state velocity;
- final pre-show snapshots for completed-day comparison;
- capacity-weighted occupancy, show share, seat share and Seat-State Performance Index.

### Dashboard

`index.html` is now a dense static analytical interface with:

- date / All Day / Matinee / Prime Time / Late controls;
- exhibitor and geography scope filters;
- latest vs final-pre-show observation mode;
- compact KPI strip;
- cinema ranking as the primary surface;
- sortable and configurable columns;
- show share, seat share and performance index;
- exhibitor comparison;
- occupancy distribution;
- day-of-run trend table;
- secondary Malaysia geography navigator;
- per-cinema session drilldown with observed changes and velocity;
- source and measurement-coverage status.

## Data layers

```text
Exhibitor/public source
        ↓
collector (source-specific acquisition)
        ↓
normalizer (source → universal session snapshot)
        ↓
/data/history/YYYY-MM-DD/*.json  immutable observations
        ↓
analytics
        ↓
/data/current.json + /data/days/*.json
        ↓
static browser dashboard
```

## Run locally

Requires Python 3.11+.

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
python -m scripts.analytics.validate_data
python -m http.server 8000
```

Then open `http://localhost:8000/`.

The generated `data/browser-data.js` compatibility mirror allows the dashboard to run by opening `index.html` directly. On GitHub Pages or ordinary HTTP hosting, the dashboard uses the canonical JSON products instead.

## Collect manually

```bash
python -m scripts.collectors.collect_all --allow-empty
```

Or collect a specified theatrical date:

```bash
python -m scripts.collectors.collect_all --date 2026-09-04 --allow-empty
```

The GitHub Actions workflow runs the same read-only acquisition hourly and commits changed `data/` products.

## Methodology

Read `docs/METHODOLOGY.md` before interpreting any metric. Source contracts are documented in `docs/SOURCES.md`.


## Current acquisition coverage

| Exhibitor | Schedule | Seat state | Source boundary |
| --- | --- | --- | --- |
| GSC | Automated | Automated | Official read-only XML endpoints |
| TGV | Automated | Automated | Official read-only API |
| Paragon | Automated | Not available | Official cinema-detail pages only |
| Mega Cineplex | Automated | Not available | Official TIKUS! movie-detail page only |

Paragon and Mega are intentionally excluded from seat-weighted occupancy and Performance Index calculations.

## Historical recovery

Recovered evidence from dates before automated collection lives under `data/recovered/`. It is not silently inserted into collector history because a retrospective webpage does not provide a defensible contemporaneous observation timestamp.

## v4 live-run hardening

The first production collection on 4 September 2026 began at 22:58 MYT, so it cannot be treated as a complete reconstruction of the theatrical day. v4 therefore separates full observed-day history from `liveSessions`, flags sessions first discovered only after showtime, and embeds latest collector diagnostics in browser products. See `docs/FIRST_LIVE_RUN_AUDIT.md`.

### v5 Paragon parser hardening

After the second live run, a false Paragon Batu Pahat `00:30` session exposed a movie-card scoping problem in the schedule parser. `paragon-schedule/1.1.0` now bounds extraction to an exact TIKUS! movie-card candidate and stops at the next Vista `Play Trailer` movie boundary. See `docs/SECOND_LIVE_RUN_AUDIT.md`.


## Correction ledger

Analytical products may exclude observations through `data/meta/corrections.json` when a collector defect is proven. Raw history is never rewritten or deleted. Each exclusion remains attributable to a correction ID and reason.

A **final pre-show** observation is only finalized after the session start time has passed, because only then can the system know which stored pre-start observation was the last one. Future sessions remain provisional and are excluded from final-pre-show metrics.

## v6 correctness controls

v6 adds an auditable correction/exclusion layer and strict finalized-pre-show semantics. `data/meta/corrections.json` never deletes raw history; it only controls eligibility for generated analytics. Paragon schedule collection now uses HTML-tree containment and reports collector version `paragon-schedule/1.2.0`.


## v7 Paragon collector

Paragon schedule acquisition now uses the exhibitor's link semantics rather than DOM ancestor guessing. `paragon-schedule/1.3.0` identifies the exact TIKUS! movie-title anchor, reads only ticketing anchors before the next movie-title anchor, scopes them by explicit show-date heading, and preserves Paragon `txtSessionId` as the native session identity. Per-cinema parser diagnostics are exposed in each collection run for source-health auditing.


## v8 schedule-only identity reconciliation

Analytical products canonicalize duplicate schedule-only identities when legacy time fingerprints and newer native source-session IDs describe the exact same provider/cinema/date/start-time screening. Native IDs win. Raw history is never rewritten, and seat-measured observations are excluded from this reconciliation rule. Targeted correction-ledger entries quarantine known false observations while retaining them for audit.

## v9 distribution intelligence

v9 adds a derived analytical layer without changing acquisition behaviour:

- Seat-State Momentum from repeated valid measurements;
- Prime-Time Efficiency for 18:00–20:59 starts;
- session velocity leaders;
- observed day-over-day show and prime-show allocation deltas;
- explicit comparison-quality gating when either theatrical day is partial.

All momentum/velocity language refers to observed source-defined seat states, never confirmed paid tickets or admissions. See `docs/METHODOLOGY.md`.

## v10 decision intelligence

v10 adds `intelligence.decisionSignals`, a cautious operational-triage layer derived from corrected observed seat-state performance, repeated-measurement momentum and prime-time utilisation. Signals are labelled **Review opportunity**, **Mixed signal**, **Capacity watch** or **Monitor**. They are not forecasts, sales estimates or automated programming recommendations. Partial-day acquisition automatically reduces confidence to low.

## v11 as-of replay

v11 adds hindsight-safe historical replay without changing acquisition. Each generated day product now exposes `asOfReplay.checkpoints` at fixed Asia/Kuala_Lumpur cutoffs (12:00, 15:00, 18:00 and 21:00 where that cutoff had actually occurred).

A replay checkpoint is rebuilt from corrected/reconciled observations whose `collectedAt` is **at or before** the cutoff. Later observations are excluded from session state, rankings, momentum, prime-time efficiency, velocity and decision signals. Intraday replay decision confidence is capped at low and allocation comparison remains limited because the current-day side is necessarily partial.

The dashboard adds **As-of replay** to the Observation selector and reveals a Replay cutoff selector. Final pre-show remains a separate observation mode because it answers a different question: the last valid pre-start observation after a session has actually begun.

## v12 session trajectory intelligence

v12 adds `intelligence.sessionTrajectories`, a comparable relative-to-showtime view for seat-measured screenings. Each screening can expose T−6h, T−3h, T−1h and finalized pre-show checkpoints. A checkpoint always uses the latest valid seat-state observation collected at or before that cutoff; later observations never backfill an earlier checkpoint.

Cinema trajectory rollups are capacity-weighted and report checkpoint coverage explicitly. `occupancyLift6hToFinal` is an observed utilisation change in percentage points, not a ticket-sales or admissions estimate. As-of replay rebuilds trajectories from its restricted knowledge history, so replayed curves remain hindsight-safe.


## v13 individual screening trajectory explorer
- Adds a screening selector inside cinema detail for seat-measured sessions.
- Displays T−6h, T−3h, T−1h and final pre-show used/capacity, occupancy, exact observation timestamp and minutes-before-show.
- Session-table rows can select the trajectory with mouse or keyboard.
- Uses the active backend trajectory object, including hindsight-safe as-of replay trajectories.
- Does not alter collectors, raw history, corrections, reconciliation, or metric semantics.

## v14 cinema comparison workspace

v14 adds a side-by-side workspace for selecting 2–4 cinemas and comparing observed allocation, capacity/utilisation, Seat-State Performance Index, momentum, prime-time efficiency, trajectory checkpoints, allocation change and Decision Signals. The workspace inherits the active date/geography/exhibitor/observation scope, including hindsight-safe as-of replay. No acquisition or metric semantics changed in this release.

## v15 comparison export
The Cinema Comparison Workspace can export the current 2–4 cinema selection as CSV or switch to a comparison-only print layout suitable for internal print/PDF circulation. Exports preserve active observation/replay scope and explicitly state that observed used/booked seat states are not confirmed paid ticket sales.
