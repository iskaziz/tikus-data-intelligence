# Seventh live-run audit — decision intelligence

## Basis

v10 builds on the corrected/reconciled v8 data model and the v9 distribution-intelligence layer. The most recent supplied live product (5 Sep 2026, 17:52 MYT) showed a mature intraday dataset with repeated GSC/TGV observations, prime-time sessions approaching, and provisional final-pre-show coverage. The new layer does not change acquisition.

## What v10 adds

`intelligence.decisionSignals` converts existing analytical evidence into cautious operational triage labels:

- **Review opportunity** — multiple positive observed indicators align.
- **Mixed signal** — positive and cautionary indicators disagree.
- **Capacity watch** — multiple cautionary observed indicators align.
- **Monitor** — evidence is insufficient or not strongly directional.

Inputs are limited to:

1. Seat-State Performance Index.
2. Recent observed seat-state momentum from repeated measurements.
3. Prime-time utilisation relative to the cinema's all-day utilisation.
4. Day-to-day observed allocation change only when the comparison is methodologically comparable.

## Guardrails

- No signal is called a forecast.
- No signal is called paid ticket sales, admissions, revenue or box office.
- No automatic allocation recommendation is issued.
- Partial-day acquisition forces signal confidence to `low`.
- Schedule-only cinemas can remain outside decision scoring when no seat-state evidence exists.
- Raw history is not changed.

## Intended use

The panel is a producer/distributor triage surface: it helps identify which cinemas deserve human review first. A signal should lead to inspection of the underlying sessions and source quality, not automatic action.
