"""Read-only Paragon schedule collector.

Reads official cinema-detail pages only. It never enters ticketing, seat
selection or basket flows. Seat metrics remain null by design.
"""
from __future__ import annotations

import re
from datetime import datetime
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

from scripts.collectors.base import Collector
from scripts.lib.http import get
from scripts.lib.registry import by_exhibitor

COLLECTOR_VERSION = "paragon-schedule/1.0.0"
TZ = ZoneInfo("Asia/Kuala_Lumpur")
BASE = "https://www.paragoncinemas.com.my/Browsing/Cinemas/Details/{code}"
DATE_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(\d{2})\s+([A-Za-z]+)\s+(\d{4})$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.I)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def _tokens(html: str) -> list[str]:
    p = _Text(); p.feed(html)
    return p.parts


def parse_tikus_times(html: str, show_date: str) -> list[str]:
    """Extract TIKUS! times for one date from the official cinema page."""
    tokens = _tokens(html)
    try:
        start = next(i for i, t in enumerate(tokens) if t.strip().casefold() == "tikus!")
    except StopIteration:
        return []
    target = datetime.strptime(show_date, "%Y-%m-%d").strftime("%A, %d %B %Y")
    in_target = False
    times: list[str] = []
    for token in tokens[start + 1:]:
        if DATE_RE.match(token):
            if in_target:
                break
            in_target = token == target
            continue
        if in_target and TIME_RE.match(token):
            times.append(token.upper())
    return times


def to_24h(value: str) -> str:
    return datetime.strptime(value, "%I:%M %p").strftime("%H:%M")


class ParagonCollector(Collector):
    exhibitor_id = "paragon"

    def collect(self, show_date: str):
        facts = []
        for cinema in by_exhibitor("paragon"):
            code = cinema.get("source", {}).get("officialCinemaId")
            if not code:
                continue
            url = BASE.format(code=code)
            response = get(url)
            for time_text in parse_tikus_times(response.text, show_date):
                facts.append({
                    "cinemaId": cinema["id"],
                    "sourceCinemaId": code,
                    "sourceCinemaName": cinema.get("name"),
                    "showDate": show_date,
                    "session": {"time": to_24h(time_text), "format": "2D", "language": "Malay"},
                    "scheduleUrl": url,
                    "schedulePayloadHash": response.sha256,
                    "errors": [],
                })
        return facts
