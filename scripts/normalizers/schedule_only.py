from __future__ import annotations

from typing import Any
from .common import start_at, minutes_to_show, session_identity


def normalize_schedule_only(*, provider: str, exhibitor_id: str, run_id: str, cinema_id: str,
                            source_cinema_id: str | None, source_cinema_name: str | None,
                            show_date: str, collected_at: str, session: dict[str, Any],
                            collector_version: str, source_url: str | None = None, raw_payload_hash: str | None = None, acquisition_warnings: list[str] | None = None) -> dict[str, Any]:
    start = start_at(show_date, session["time"])
    source_session_id = str(session.get("sessionId")) if session.get("sessionId") is not None else None
    return {
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "filmId": "tikus",
        "cinemaId": cinema_id,
        "exhibitorId": exhibitor_id,
        "sessionId": session_identity(cinema_id, show_date, session["time"], source_session_id, session.get("hall")),
        "sourceSessionId": source_session_id,
        "source": {
            "provider": provider, "sourceType": "official-public-page" if provider == "paragon" else "public-listing",
            "sourceCinemaId": source_cinema_id, "sourceCinemaName": source_cinema_name,
            "sourceUrl": source_url, "collectorVersion": collector_version, "rawPayloadHash": raw_payload_hash
        },
        "collectedAt": collected_at,
        "showDate": show_date,
        "startAt": start,
        "minutesToShow": minutes_to_show(collected_at, start),
        "session": {
            "auditorium": session.get("hall"), "format": session.get("format"),
            "language": session.get("language"), "experience": None
        },
        "seat": {"capacity": None, "used": None, "available": None, "otherUnavailable": None, "statusCounts": None},
        "semantics": {"used": "unavailable", "available": "unavailable", "capacity": "unavailable"},
        "quality": {
            "measurementStatus": "schedule-only", "seatMeasured": False,
            "warnings": ["No public seat count is used or inferred.", *(acquisition_warnings or [])]
        }
    }
