#!/usr/bin/env python3
"""Convert the previous tracker current.json shape into normalized snapshots.

This adapter is deliberately conservative. Records lacking a reconstructable
show date/time or semantics are skipped instead of guessed.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Kuala_Lumpur")
ID_MAP = {
    "gsc-midvalley": "gsc-mid-valley",
    "tgv-tebrau": "tgv-tebrau-city",
    "mega-riverfront": "mega-riverfront-mall",
}
CHAIN_MAP = {"GSC": "gsc", "TGV": "tgv", "Paragon": "paragon", "PARAGON": "paragon", "Mega": "mega", "MEGA": "mega"}


def normalize_id(value: str) -> str:
    return ID_MAP.get(value, value)


def iso_start(show_date: str, hhmm: str) -> str:
    return datetime.fromisoformat(f"{show_date}T{hhmm}:00").replace(tzinfo=TZ).isoformat()


def convert_session(cinema: dict, session: dict, show_date: str, legacy_file: Path, run_id: str):
    if not session.get("time"):
        return None
    exhibitor = CHAIN_MAP.get(cinema.get("chain"))
    if not exhibitor:
        return None

    cinema_id = normalize_id(cinema["id"])
    native_session = session.get("sessionId")
    start_at = iso_start(show_date, session["time"])
    internal_id = f"{cinema_id}:{show_date}:{session['time']}:{native_session or 'legacy'}"
    observed_at = session.get("seatObservedAt") or session.get("observedAt")
    if observed_at is None:
        return None

    capacity = session.get("capacity")
    used = session.get("booked")
    available = session.get("available")
    other = session.get("otherUnavailable")
    seat_measured = isinstance(capacity, int) and isinstance(used, int) and capacity > 0

    if exhibitor == "gsc" and seat_measured:
        semantics = {
            "used": "gsc-booked-state-B",
            "available": "gsc-available-state-A",
            "capacity": "gsc-observed-seat-map",
        }
    elif exhibitor == "tgv" and seat_measured:
        semantics = {
            "used": "tgv-seatsused",
            "available": "derived-capacity-minus-used",
            "capacity": "tgv-seatstotal",
        }
    else:
        semantics = {"used": "unavailable", "available": "unavailable", "capacity": "unavailable"}

    return {
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "filmId": "tikus",
        "cinemaId": cinema_id,
        "exhibitorId": exhibitor,
        "sessionId": internal_id,
        "sourceSessionId": str(native_session) if native_session is not None else None,
        "source": {
            "provider": "legacy-import",
            "sourceType": "legacy-import",
            "sourceCinemaId": str(cinema.get("officialLocationId") or cinema.get("officialCinemaId") or "") or None,
            "sourceCinemaName": cinema.get("officialCinemaName") or cinema.get("name"),
            "sourceUrl": cinema.get("sourceUrl"),
            "collectorVersion": "legacy-current-import-v1",
            "rawPayloadHash": None,
        },
        "collectedAt": observed_at,
        "showDate": show_date,
        "startAt": start_at,
        "minutesToShow": None,
        "session": {
            "auditorium": session.get("hall"),
            "format": session.get("type"),
            "language": None,
            "experience": session.get("experience"),
        },
        "seat": {
            "capacity": capacity if seat_measured else None,
            "used": used if seat_measured else None,
            "available": available if seat_measured and isinstance(available, int) else None,
            "otherUnavailable": other if seat_measured and isinstance(other, int) else None,
            "statusCounts": session.get("statusCounts") if seat_measured else None,
        },
        "semantics": semantics,
        "quality": {
            "measurementStatus": "complete" if seat_measured else "schedule-only",
            "seatMeasured": seat_measured,
            "warnings": [
                "Imported from the previous TIKUS! tracker; provenance retained.",
                "Observed seat state is not confirmed paid ticket sales."
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("legacy_current", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    legacy = json.loads(args.legacy_current.read_text(encoding="utf-8"))
    show_date = legacy.get("date")
    if not show_date:
        raise SystemExit("Legacy file has no top-level date; refusing to guess")
    run_id = f"legacy-import:{legacy.get('updatedAt') or show_date}"

    snapshots = []
    skipped = 0
    for cinema in legacy.get("cinemas", []):
        for session in cinema.get("sessions", []):
            item = convert_session(cinema, session, show_date, args.legacy_current, run_id)
            if item is None:
                skipped += 1
            else:
                snapshots.append(item)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"snapshots": snapshots, "skipped": skipped}, indent=2), encoding="utf-8")
    print(f"Imported {len(snapshots)} snapshots; skipped {skipped} ambiguous records")


if __name__ == "__main__":
    main()
