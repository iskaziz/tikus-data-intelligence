# TIKUS! Data Intelligence v18 — Multi-Day Executive Trend Briefing Audit

## Scope
v18 is a presentation-layer enhancement. It does not change collectors, source semantics, correction rules, schedule-only reconciliation, immutable history, or backend product schema.

## New capability
The condensed briefing now includes a multi-day trend for the same 2–4 selected cinemas.

### Finalized theatrical days
A day is admitted to the finalized table only when `finalPreShowState.status === "complete"`.
The table uses that product's `finalPreShowSessions` only. Latest-observed intraday values are never substituted into a completed-day trend.

### Partial / provisional days
Days that are not complete are rendered separately. They use latest eligible observed sessions. When the active date is in As-of replay mode, the current day's provisional row uses the active replay's session set, preserving the no-hindsight rule.

## Display semantics
Each cinema/day cell shows observed show count and capacity-weighted observed occupancy. The selected-total column aggregates only the chosen cinemas under the active time/exhibitor/geography scope.

The two tables are visually and semantically separate so a partial/current day cannot be mistaken for finalized pre-show performance.

## Safety / interpretation
Observed used/booked states are not confirmed paid ticket sales. Schedule-only cinemas can contribute observed show allocation but not seat-state occupancy.

## Validation
- 40/40 tests passing
- Python compilation passing
- JavaScript syntax checks passing
- semantic data validation passing
- new briefing DOM/interface targets verified
