"""Read-only official TGV API collector for TIKUS!.

Uses only session discovery and seat-status endpoints. It does not invoke seat
selection, order creation, checkout, or payment endpoints.
"""
from __future__ import annotations

from typing import Any

from scripts.collectors.base import Collector
from scripts.lib import http
from scripts.lib.registry import by_source_id

COLLECTOR_VERSION = "1.0.0"
MOVIE_RECID = "7b2216d1-27d8-479e-b420-8ab157847aa6"
SCHEDULE_ENDPOINT = "https://api.tgv.com.my/api/boxoffice/v1/moviesession_get"
SEAT_ENDPOINT = "https://api.tgv.com.my/api/boxoffice/v1/moviesession_getseatstatus"
HEADERS = {"Origin": "https://www.tgv.com.my", "Referer": "https://www.tgv.com.my/"}


def extract_sessions(payload: dict[str, Any], source_cinema_id: str) -> tuple[str | None, list[dict[str, Any]]]:
    """Extract the documented nested movies→experiences→sessions structure."""
    businessday = ((payload.get("results") or {}).get("businessday") or {})
    cinema_nodes = businessday.get("cinemas") or []
    for cinema in cinema_nodes:
        if str(cinema.get("cinemaid")) != str(source_cinema_id):
            continue
        source_name = cinema.get("name")
        sessions: list[dict[str, Any]] = []
        for movie in cinema.get("movies") or []:
            if movie.get("movieid") != MOVIE_RECID:
                continue
            for exp_group in movie.get("experiences") or []:
                group_experience = exp_group.get("experience")
                for item in exp_group.get("sessions") or []:
                    showtimemy = item.get("showtimemy")
                    if not item.get("sessionid") or not showtimemy:
                        continue
                    time_part = showtimemy.split("T", 1)[-1][:5]
                    sessions.append({
                        "sessionId": str(item.get("sessionid")),
                        "time": time_part,
                        "showDate": item.get("businessdate") or businessday.get("businessday"),
                        "showtimemy": showtimemy,
                        "hall": item.get("screenname"),
                        "scheduledFilmId": item.get("scheduledfilmid"),
                        "experience": item.get("experience") or group_experience,
                        "seatTypes": item.get("seattypes"),
                        "format": _format_from_extdata(item.get("extdata")),
                        "raw": item,
                    })
        return source_name, sessions
    return None, []


def _format_from_extdata(extdata: Any) -> str | None:
    if not isinstance(extdata, dict):
        return None
    names = extdata.get("conceptattributenames")
    if isinstance(names, list) and names:
        return ", ".join(str(x) for x in names)
    return None


def _int_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def extract_seat_status(payload: dict[str, Any]) -> dict[str, dict[str, int | None]]:
    status_list = (((payload.get("results") or {}).get("seatstatuslist")) or [])
    out: dict[str, dict[str, int]] = {}
    for item in status_list:
        sid = item.get("sessionid")
        total = item.get("seatstotal")
        used = item.get("seatsused")
        if sid is None:
            continue
        out[str(sid)] = {
            "seatstotal": _int_value(total),
            "seatsused": _int_value(used),
            "usedpercentage": item.get("usedpercentage"),
        }
    return out


class TGVCollector(Collector):
    exhibitor_id = "tgv"
    movie_recid = MOVIE_RECID

    def collect(self, show_date: str) -> list[dict[str, Any]]:
        tracked = by_source_id("tgv")
        output: list[dict[str, Any]] = []
        for source_cinema_id, cinema in tracked.items():
            schedule_payload = {
                "cinemaid": source_cinema_id,
                "businessdate": show_date,
                "movieid": MOVIE_RECID,
                "retrieveexpired": False,
            }
            schedule_response = http.post_json(SCHEDULE_ENDPOINT, schedule_payload, headers=HEADERS)
            schedule_json = schedule_response.json()
            if schedule_json.get("success") is False:
                raise ValueError(f"TGV schedule API returned success=false for {source_cinema_id}: {schedule_json.get('error')}")
            source_name, sessions = extract_sessions(schedule_json, source_cinema_id)
            session_ids = [s["sessionId"] for s in sessions]
            seat_by_session: dict[str, dict[str, int]] = {}
            seat_hash = None
            seat_error = None
            if session_ids:
                try:
                    seat_response = http.post_json(SEAT_ENDPOINT, {"cinemaid": source_cinema_id, "sessionid": session_ids}, headers=HEADERS)
                    seat_by_session = extract_seat_status(seat_response.json())
                    seat_hash = seat_response.sha256
                except Exception as exc:
                    seat_error = f"seat-status: {type(exc).__name__}: {exc}"

            for source_session in sessions:
                seat = seat_by_session.get(source_session["sessionId"])
                normalized_session = {
                    "time": source_session["time"],
                    "sessionId": source_session["sessionId"],
                    "hall": source_session["hall"],
                    "experience": source_session["experience"],
                    "format": source_session["format"],
                    "language": None,
                    "seatstotal": seat.get("seatstotal") if seat else None,
                    "seatsused": seat.get("seatsused") if seat else None,
                    "usedpercentage": seat.get("usedpercentage") if seat else None,
                }
                errors = [seat_error] if seat_error else ([] if seat else ["seat-status: no matching session returned"])
                output.append({
                    "cinemaId": cinema["id"],
                    "sourceCinemaId": source_cinema_id,
                    "sourceCinemaName": source_name or (cinema["source"].get("officialNames") or [cinema["name"]])[0],
                    "showDate": source_session["showDate"] or show_date,
                    "session": normalized_session,
                    "scheduledFilmId": source_session["scheduledFilmId"],
                    "seatTypes": source_session["seatTypes"],
                    "schedulePayloadHash": schedule_response.sha256,
                    "seatPayloadHash": seat_hash,
                    "scheduleUrl": SCHEDULE_ENDPOINT,
                    "seatStatusUrl": SEAT_ENDPOINT,
                    "errors": [x for x in errors if x],
                })
        return output
