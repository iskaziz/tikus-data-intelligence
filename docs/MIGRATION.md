# Migration from the previous TIKUS! tracker

The new repository migrates **source knowledge**, not the old tracker interface or its browser-facing data model.

## Preserve

- the producer-confirmed 16-cinema allocation;
- GSC official location IDs and aliases;
- GSC public seat-state interpretation: `A` available, `B` booked-state, others separate;
- TGV official cinema IDs and TIKUS! movie/session identifiers;
- TGV official API knowledge around `seatstotal` and `seatsused`;
- Paragon cinema codes and public session IDs where available;
- Mega Riverfront public schedule source identifier;
- source-specific date/time parsing knowledge;
- known retry/error cases;
- historical recovery knowledge, but only with explicit provenance.

## Reimplement

Every exhibitor becomes a small collector + normalizer pair returning the universal snapshot schema.

No collector should calculate ranking, shares, occupancy distribution or dashboard totals. Those belong in analytics.

## Do not migrate

- old tracker HTML/CSS;
- old map implementation;
- old status cards or visual hierarchy;
- UI-coupled calculations;
- aggregate JSON shapes that lose observation-level provenance;
- `booked == paid sale` assumptions;
- zero-filling for missing seat data;
- any automation that selects seats or creates holds.

## Canonical ID remaps

The new canonical IDs intentionally standardize several legacy names:

| Legacy ID/name | New canonical ID/name |
|---|---|
| `gsc-midvalley` | `gsc-mid-valley` — GSC Mid Valley Megamall |
| `tgv-tebrau` | `tgv-tebrau-city` — TGV Tebrau City |
| `mega-riverfront` | `mega-riverfront-mall` — Mega Cineplex Riverfront Mall |
| `Paragon Cinemas Batu Pahat` | Paragon Batu Pahat |
| `Paragon Cinema KTCC` | Paragon KTCC |
| TGV source `SUNWAY WANGSA MALL` | display remains TGV Wangsa Walk |
| TGV source `GURNEY PARAGON` | display remains TGV Gurney |

## Historical import policy

An old observation is importable only when its meaning can be reconstructed with enough confidence to populate:

- collection time;
- cinema;
- show date/time;
- stable/native session identity where possible;
- seat semantics;
- provenance.

Imported snapshots carry `provider: legacy-import` and should never overwrite native historical observations.

Ambiguous old records should be excluded rather than guessed.
