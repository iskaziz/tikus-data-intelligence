from __future__ import annotations

from typing import Any
from .common import start_at, minutes_to_show, session_identity


def normalize_tgv(*, run_id: str, cinema_id: str, source_cinema_id: str, source_cinema_name: str,
                  show_date: str, collected_at: str, session: dict[str, Any], collector_version: str,
                  source_url: str | None = None, raw_payload_hash: str | None = None, acquisition_warnings: list[str] | None = None) -> dict[str, Any]:
    """Normalize one already-acquired TGV official API session fact."""
    capacity = session.get("seatstotal")
    used = session.get("seatsused")
    measured = isinstance(capacity, int) and capacity > 0 and isinstance(used, int) and 0 <= used <= capacity
    available = capacity - used if measured else None
    start = start_at(show_date, session["time"])
    source_session_id = str(session.get("sessionId")) if session.get("sessionId") is not None else None

    return {
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "filmId": "tikus",
        "cinemaId": cinema_id,
        "exhibitorId": "tgv",
        "sessionId": session_identity(cinema_id, show_date, session["time"], source_session_id, session.get("hall")),
        "sourceSessionId": source_session_id,
        "source": {
            "provider": "tgv", "sourceType": "official-api", "sourceCinemaId": source_cinema_id,
            "sourceCinemaName": source_cinema_name, "sourceUrl": source_url,
            "collectorVersion": collector_version, "rawPayloadHash": raw_payload_hash
        },
        "collectedAt": collected_at,
        "showDate": show_date,
        "startAt": start,
        "minutesToShow": minutes_to_show(collected_at, start),
        "session": {
            "auditorium": session.get("hall"), "format": session.get("format"),
            "language": session.get("language"), "experience": session.get("experience")
        },
        "seat": {
            "capacity": capacity if measured else None,
            "used": used if measured else None,
            "available": available,
            "otherUnavailable": None,
            "statusCounts": None
        },
        "semantics": {
            "used": "tgv-seatsused" if measured else "unavailable",
            "available": "derived-capacity-minus-used" if measured else "unavailable",
            "capacity": "tgv-seatstotal" if measured else "unavailable"
        },
        "quality": {
            "measurementStatus": "complete" if measured else "partial",
            "seatMeasured": measured,
            "warnings": ["TGV seatsused may include held or otherwise unavailable inventory.", *(acquisition_warnings or [])]
        }
    }
