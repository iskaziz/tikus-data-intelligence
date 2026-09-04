# Next-stage implementation notes

This package advances the GitHub main branch with:

1. Automated read-only Paragon schedule acquisition from the official Batu Pahat and KTCC cinema pages.
2. Automated read-only Mega Cineplex schedule acquisition from the official TIKUS! movie page (movie ID 3788), scoped to Riverfront, Sungai Petani.
3. Both sources remain schedule-only. No seat inventory is inferred or requested through booking flows.
4. `collect_all` now defaults to `gsc,tgv,paragon,mega`.
5. Parser fixtures and tests for both new schedule collectors.
6. A separate `data/recovered/` evidence layer for retrospective schedule recovery.
7. Verified launch-day Paragon schedule evidence for 3 September 2026, kept separate from contemporaneous collector history.

All 15 tests pass and the data-contract validator passes.
