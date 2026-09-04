from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Asia/Kuala_Lumpur")


def start_at(show_date: str, hhmm: str) -> str:
    return datetime.fromisoformat(f"{show_date}T{hhmm}:00").replace(tzinfo=TZ).isoformat()


def minutes_to_show(collected_at: str, start_at_iso: str) -> int:
    collected = datetime.fromisoformat(collected_at)
    start = datetime.fromisoformat(start_at_iso)
    return round((start - collected).total_seconds() / 60)


def session_identity(cinema_id: str, show_date: str, hhmm: str, source_session_id: str | None, auditorium: str | None = None) -> str:
    # Native exhibitor session IDs take precedence so repeated observations,
    # including a legitimate schedule-time change, remain one historical entity.
    if source_session_id:
        return f"{cinema_id}:source:{source_session_id}"
    stable = auditorium or "unknown"
    return f"{cinema_id}:fingerprint:{show_date}:{hhmm}:{stable}"
