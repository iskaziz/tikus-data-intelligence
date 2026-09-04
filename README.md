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
