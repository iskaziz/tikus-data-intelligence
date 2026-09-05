# v15 — Comparison Export / Share Engineering Audit

## Scope
v15 adds a compact internal export/share surface to the existing Cinema Comparison Workspace. No acquisition, correction, reconciliation, analytics, or schema behavior changes.

## CSV export
- Exports one row per selected cinema (2–4).
- Carries show date, observation mode, replay cutoff when applicable, allocation, observed capacity and used/booked state, occupancy, Seat-State Performance Index, momentum, prime-time efficiency, trajectory checkpoints, allocation delta, and Decision Signal/confidence.
- Includes an explicit first-line caveat that observed used/booked state is not confirmed paid ticket sales.
- Runs entirely in-browser using a Blob; no backend is introduced.

## Print report
- Print action switches the page into a dedicated comparison-only print layout.
- Report includes TIKUS! Data Intelligence label, active analytical scope, selected cinema names, and methodology caveat.
- Dashboard navigation, selectors, filters, and unrelated panels are hidden in print.
- Landscape layout is used to preserve side-by-side comparison readability.

## Methodology safeguards
- Export and print consume the same selected comparison records already rendered by v14.
- As-of replay metadata is preserved in the output when replay is active.
- No client-side reinterpretation of backend intelligence metrics is introduced.
- No paid-sales terminology is introduced.
