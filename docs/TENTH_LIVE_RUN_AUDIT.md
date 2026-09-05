# Tenth engineering audit — v13 screening trajectory explorer

This release is presentation-only on top of v12 trajectory data. The explorer consumes backend-generated trajectory checkpoints rather than recomputing them in JavaScript. Therefore checkpoint eligibility and anti-hindsight semantics remain centralized in Python.

The interface exposes exact observation timestamps and minutes-before-show so users can distinguish a checkpoint represented by an observation close to the target cutoff from one represented by an older available observation. Missing checkpoints remain visibly unavailable; no interpolation is performed.

No acquisition, correction, session reconciliation, or seat-state semantics changed.
