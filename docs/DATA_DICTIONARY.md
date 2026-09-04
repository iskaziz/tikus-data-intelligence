# Data Dictionary

## Normalized session snapshot

| Field | Type | Meaning |
|---|---|---|
| `schemaVersion` | string | Data-contract version. |
| `runId` | string | Identifier for one collector run. |
| `filmId` | string | Always `tikus`. |
| `cinemaId` | string | Canonical repository cinema ID. |
| `exhibitorId` | enum | `gsc`, `tgv`, `paragon`, `mega`. |
| `sessionId` | string | Stable internal session identity. |
| `sourceSessionId` | string/null | Native exhibitor/session identifier when available. |
| `collectedAt` | datetime | When the public state was observed. |
| `showDate` | date | Local theatrical date. |
| `startAt` | datetime | Local show start represented as an offset-aware ISO datetime. |
| `minutesToShow` | integer/null | Difference between `startAt` and `collectedAt`. |
| `session.auditorium` | string/null | Hall/auditorium if observed. |
| `session.format` | string/null | 2D or other source-provided format. |
| `session.language` | string/null | Only when observed from source. |
| `session.experience` | string/null | Source-provided experience such as TGV Deluxe. |
| `seat.capacity` | integer/null | Observed allocated capacity where measurable. |
| `seat.used` | integer/null | Source-defined used/booked state; never automatically tickets sold. |
| `seat.available` | integer/null | Directly observed or explicitly derived remaining inventory. |
| `seat.otherUnavailable` | integer/null | Separately observed unavailable states not included in `used`. |
| `seat.statusCounts` | object/null | Raw normalized state-count map where available. |
| `semantics.used` | enum | Exact interpretation of `seat.used`. |
| `semantics.available` | enum | Exact interpretation of `seat.available`. |
| `semantics.capacity` | enum | Exact interpretation of `seat.capacity`. |
| `quality.measurementStatus` | enum | `complete`, `partial`, `schedule-only`, `stale`, `error`. |
| `quality.seatMeasured` | boolean | Whether the snapshot is eligible for seat-weighted metrics. |
| `quality.warnings` | array | Human-readable caveats attached to the observation. |

## Derived metric types

The UI should visually distinguish metric classes:

- absolute values: `742`;
- shares: `17.8%`;
- ratios: `1.24×`;
- changes: `+18`;
- velocity: `+2.6 / hr`;
- coverage: `31 / 37`.


## Correction ledger

Analytical products may exclude observations through `data/meta/corrections.json` when a collector defect is proven. Raw history is never rewritten or deleted. Each exclusion remains attributable to a correction ID and reason.

A **final pre-show** observation is only finalized after the session start time has passed, because only then can the system know which stored pre-start observation was the last one. Future sessions remain provisional and are excluded from final-pre-show metrics.
