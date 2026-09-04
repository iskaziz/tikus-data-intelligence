from __future__ import annotations

from typing import Any
from .common import start_at, minutes_to_show, session_identity


def normalize_gsc(*, run_id: str, cinema_id: str, source_cinema_id: str, source_cinema_name: str,
                  show_date: str, collected_at: str, session: dict[str, Any], collector_version: str,
                  source_url: str | None = None, raw_payload_hash: str | None = None, acquisition_warnings: list[str] | None = None) -> dict[str, Any]:
    """Normalize one already-acquired GSC public seat-state fact.

    Expected `session` keys include time, sessionId and statusCounts. This
    function never fetches or modifies booking inventory.
    """
    counts = {str(k): int(v) for k, v in (session.get("statusCounts") or {}).items()}
    available = counts.get("A", 0)
    used = counts.get("B", 0)
    other = sum(v for k, v in counts.items() if k not in {"A", "B"})
    capacity = sum(counts.values()) if counts else None
    measured = capacity is not None and capacity > 0
    start = start_at(show_date, session["time"])
    source_session_id = str(session.get("sessionId")) if session.get("sessionId") is not None else None

    return {
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "filmId": "tikus",
        "cinemaId": cinema_id,
        "exhibitorId": "gsc",
        "sessionId": session_identity(cinema_id, show_date, session["time"], source_session_id, session.get("hall")),
        "sourceSessionId": source_session_id,
        "source": {
            "provider": "gsc", "sourceType": "official-api", "sourceCinemaId": source_cinema_id,
            "sourceCinemaName": source_cinema_name, "sourceUrl": source_url,
            "collectorVersion": collector_version, "rawPayloadHash": raw_payload_hash
        },
        "collectedAt": collected_at,
        "showDate": show_date,
        "startAt": start,
        "minutesToShow": minutes_to_show(collected_at, start),
        "session": {
            "auditorium": session.get("hall"), "format": session.get("type"),
            "language": None, "experience": None
        },
        "seat": {
            "capacity": capacity if measured else None,
            "used": used if measured else None,
            "available": available if measured else None,
            "otherUnavailable": other if measured else None,
            "statusCounts": counts if measured else None
        },
        "semantics": {
            "used": "gsc-booked-state-B" if measured else "unavailable",
            "available": "gsc-available-state-A" if measured else "unavailable",
            "capacity": "gsc-observed-seat-map" if measured else "unavailable"
        },
        "quality": {
            "measurementStatus": "complete" if measured else "partial",
            "seatMeasured": measured,
            "warnings": ["Booked-state seats are not confirmed paid ticket sales.", *(acquisition_warnings or [])]
        }
    }
