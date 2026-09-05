# v17 Engineering Audit — Condensed Briefing Mode

## Scope

This release is presentation-only. It introduces no acquisition or analytical-semantic changes.

## Implemented

- Added `Briefing mode` action to Cinema Comparison Workspace.
- Added condensed briefing view containing headline comparison KPIs, per-cinema operational cards, trajectory table and Decision Signal evidence.
- Added `brief=1` to the existing shareable hash contract.
- Added briefing-specific copy-link and exit controls.
- Preserved active date, time, exhibitor, geography, observation mode, replay cutoff and cinema selection when entering/exiting briefing mode.
- Added responsive behavior for mobile/internal review.

## Correctness

The briefing renderer consumes `selectedComparisonRecords()` and `currentIntelligence()`, the same analytical sources used by the full comparison workspace. As-of replay therefore remains restricted to the replay checkpoint's hindsight-safe intelligence object.

Observed seat-state language remains unchanged: GSC booked-state and TGV `seatsused` are not presented as paid ticket sales.

## Verification

- Unit suite includes dedicated briefing surface/hash test.
- Semantic validator passes.
- Python compilation passes.
- JavaScript syntax check passes.
- Required briefing DOM targets and JS references verified.
