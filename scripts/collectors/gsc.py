"""Read-only GSC collector for TIKUS!.

The collector uses the public XML endpoints already exposed by GSC's own
showtime application. It never opens a transaction, selects a seat, or creates
a hold.
"""
from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlencode
from xml.etree import ElementTree as ET

from scripts.collectors.base import Collector
from scripts.lib import http
from scripts.lib.registry import by_source_id

COLLECTOR_VERSION = "1.0.0"
PARENT_ID = "6363"
SHOWTIMES_ENDPOINT = "https://epaymentapi.gsc.com.my/showtimews/service.asmx/getShowTimesByMovie_ParentChild_V2"
SEATS_ENDPOINT = "https://epaymentapi.gsc.com.my/showtimews/service.asmx/getHallSeatStatus"
HEADERS = {"Origin": "https://epaymentwebapp.gsc.com.my", "Referer": "https://epaymentwebapp.gsc.com.my/"}


def parse_showtimes_xml(xml_text: str, tracked_by_source_id: dict[str, dict]) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    facts: list[dict[str, Any]] = []
    for location in root.findall(".//location"):
        source_cinema_id = location.get("id")
        cinema = tracked_by_source_id.get(str(source_cinema_id))
        if not cinema:
            continue
        source_name = location.get("name") or cinema["name"]
        for show in location.findall(".//show"):
            raw_time = (show.get("time") or "").strip()
            if len(raw_time) != 4 or not raw_time.isdigit():
                continue
            facts.append({
                "cinemaId": cinema["id"],
                "sourceCinemaId": str(source_cinema_id),
                "sourceCinemaName": source_name,
                "sessionId": show.get("id"),
                "showDate": show.get("date"),
                "time": f"{raw_time[:2]}:{raw_time[2:]}",
                "showtimeRaw": raw_time,
                "hallId": show.get("hid"),
                "hall": show.get("hname") or show.get("hid"),
                "type": show.get("type_desc") or show.get("type"),
                "hallFull": show.get("hallfull"),
            })
    return facts


def parse_seat_status_xml(xml_text: str) -> dict[str, Any]:
    root = ET.fromstring(xml_text)
    counts: Counter[str] = Counter()
    seat_type_counts: Counter[str] = Counter()
    for node in root.findall(".//col"):
        status = node.get("status")
        if status:
            counts[status] += 1
        seat_type = node.get("type")
        if seat_type:
            seat_type_counts[seat_type] += 1
    return {
        "hall": root.get("no"),
        "statusCounts": dict(counts),
        "seatTypeCounts": dict(seat_type_counts),
        "maximumSelectableSeats": _int_or_none(root.get("maximumseats")),
        "rawHallBooked": _int_or_none(root.get("hbooked")),
        "rawHallBlocked": _int_or_none(root.get("hblocked")),
        "houseSeatsReleased": root.get("hsereleased"),
        "reservedReleased": root.get("resvreleased"),
    }


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value is not None else None
    except ValueError:
        return None


class GSCCollector(Collector):
    exhibitor_id = "gsc"

    def collect(self, show_date: str) -> list[dict[str, Any]]:
        tracked = by_source_id("gsc")
        show_url = f"{SHOWTIMES_ENDPOINT}?{urlencode({'parentid': PARENT_ID, 'oprndate': show_date})}"
        show_response = http.get(show_url, headers=HEADERS)
        schedules = parse_showtimes_xml(show_response.text, tracked)
        output: list[dict[str, Any]] = []

        for schedule in schedules:
            session = {
                "time": schedule["time"],
                "sessionId": schedule["sessionId"],
                "hall": schedule["hall"],
                "type": schedule["type"],
                "statusCounts": None,
            }
            errors: list[str] = []
            seat_hash = None
            hall_id = schedule.get("hallId")
            if hall_id:
                seat_url = f"{SEATS_ENDPOINT}?{urlencode({'locationid': schedule['sourceCinemaId'], 'hallid': hall_id, 'showdate': show_date, 'showtime': schedule['showtimeRaw']})}"
                try:
                    seat_response = http.get(seat_url, headers=HEADERS)
                    seat_data = parse_seat_status_xml(seat_response.text)
                    session.update(seat_data)
                    seat_hash = seat_response.sha256
                except Exception as exc:  # preserve schedule even if seat endpoint fails
                    errors.append(f"seat-status: {type(exc).__name__}: {exc}")
                    seat_url = None
            else:
                seat_url = None
                errors.append("seat-status: missing hall identifier")

            output.append({
                **schedule,
                "session": session,
                "showtimesUrl": show_url,
                "seatStatusUrl": seat_url,
                "showtimesPayloadHash": show_response.sha256,
                "seatPayloadHash": seat_hash,
                "errors": errors,
            })
        return output
