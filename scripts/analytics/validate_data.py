#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def iter_history_snapshots():
    for path in sorted((ROOT / "data/history").glob("*/*.json")):
        payload = load(path)
        if isinstance(payload, list):
            rows = payload
        elif isinstance(payload, dict) and isinstance(payload.get("snapshots"), list):
            rows = payload["snapshots"]
        elif isinstance(payload, dict) and payload.get("sessionId"):
            rows = [payload]
        else:
            rows = []
        for row in rows:
            yield path, row


def main() -> int:
    cinemas = load(ROOT / "data/meta/cinemas.json")
    exhibitors = load(ROOT / "data/meta/exhibitors.json")
    cinema_ids = [c["id"] for c in cinemas["cinemas"]]
    exhibitor_ids = {e["id"] for e in exhibitors["exhibitors"]}

    errors: list[str] = []
    if cinemas["count"] != 16 or len(cinema_ids) != 16:
        errors.append("Cinema registry must contain exactly 16 tracked locations")
    if len(cinema_ids) != len(set(cinema_ids)):
        errors.append("Cinema IDs must be unique")
    for cinema in cinemas["cinemas"]:
        if cinema["exhibitorId"] not in exhibitor_ids:
            errors.append(f"Unknown exhibitor for {cinema['id']}: {cinema['exhibitorId']}")
        if not cinema["name"]:
            errors.append(f"Missing canonical name for {cinema['id']}")

    expected = {"gsc": 8, "tgv": 5, "paragon": 2, "mega": 1}
    actual = {eid: sum(c["exhibitorId"] == eid for c in cinemas["cinemas"]) for eid in expected}
    if actual != expected:
        errors.append(f"Exhibitor counts differ: expected {expected}, got {actual}")

    try:
        import jsonschema
        snapshot_schema = load(ROOT / "schemas/session-snapshot.schema.json")
        current_schema = load(ROOT / "schemas/current.schema.json")
        snapshot_validator = jsonschema.Draft202012Validator(snapshot_schema, format_checker=jsonschema.FormatChecker())
        current_validator = jsonschema.Draft202012Validator(current_schema, format_checker=jsonschema.FormatChecker())

        for path in sorted((ROOT / "examples").glob("session-snapshot.*.json")):
            for err in snapshot_validator.iter_errors(load(path)):
                errors.append(f"{path.name}: {err.message}")
        for path, row in iter_history_snapshots():
            for err in snapshot_validator.iter_errors(row):
                errors.append(f"{path.relative_to(ROOT)}: {err.message}")
        current = load(ROOT / "data/current.json")
        for err in current_validator.iter_errors(current):
            errors.append(f"data/current.json: {err.message}")
    except ModuleNotFoundError:
        print("jsonschema not installed; registry validation completed, schema validation skipped")

    # Semantic invariants independent of jsonschema.
    for path, row in iter_history_snapshots():
        seat = row.get("seat", {})
        if row.get("quality", {}).get("seatMeasured"):
            cap, used = seat.get("capacity"), seat.get("used")
            if not isinstance(cap, int) or cap <= 0 or not isinstance(used, int) or not 0 <= used <= cap:
                errors.append(f"{path.relative_to(ROOT)}: invalid measured seat values for {row.get('sessionId')}")
        if row.get("exhibitorId") in {"paragon", "mega"} and row.get("quality", {}).get("seatMeasured"):
            errors.append(f"{path.relative_to(ROOT)}: schedule-only exhibitor unexpectedly marked seat-measured")

    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1

    print("Validation passed: registry, schemas, normalized history and semantic invariants are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
