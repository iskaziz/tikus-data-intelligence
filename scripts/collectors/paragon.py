"""Read-only Paragon schedule collector.

Reads official cinema-detail pages only. It never enters ticketing, seat
selection or basket flows. Seat metrics remain null by design.

The Vista/Paragon cinema page contains several movie cards and can repeat
film-title text outside the actual schedule card. Parsing is therefore
bounded to the TIKUS! card: an exact TIKUS! title token must be followed by
its own schedule/date content, and extraction stops at the next movie-card
boundary (normally ``Play Trailer``) or the next title-like section marker.
"""
from __future__ import annotations

import re
from datetime import datetime
from html.parser import HTMLParser

from scripts.collectors.base import Collector
from scripts.lib.http import get
from scripts.lib.registry import by_exhibitor

COLLECTOR_VERSION = "paragon-schedule/1.1.0"
BASE = "https://www.paragoncinemas.com.my/Browsing/Cinemas/Details/{code}"
DATE_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(\d{2})\s+([A-Za-z]+)\s+(\d{4})$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.I)

# Vista pages use this label at the start of each movie card. Bounding on it
# prevents a time from a neighbouring film from leaking into TIKUS!.
MOVIE_BOUNDARY_TOKENS = {"play trailer"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str):
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def _tokens(html: str) -> list[str]:
    p = _Text()
    p.feed(html)
    return p.parts


def _candidate_sections(tokens: list[str]) -> list[list[str]]:
    """Return bounded token sections beginning at each exact TIKUS! title.

    Real Paragon pages may contain more than one exact title occurrence. We
    inspect every candidate rather than trusting the first occurrence.
    """
    sections: list[list[str]] = []
    starts = [i for i, token in enumerate(tokens) if token.strip().casefold() == "tikus!"]
    for start in starts:
        section: list[str] = []
        for token in tokens[start + 1:]:
            if token.strip().casefold() in MOVIE_BOUNDARY_TOKENS:
                break
            section.append(token)
        sections.append(section)
    return sections


def _times_from_section(section: list[str], target: str) -> list[str]:
    # A real Paragon/Vista movie schedule card contains the future-date
    # toggle label. Stray title mentions elsewhere on the page do not.
    has_schedule_marker = any(
        "future dates" in token.casefold() for token in section
    )
    if not has_schedule_marker:
        return []

    in_target = False
    times: list[str] = []
    saw_target = False
    for token in section:
        if DATE_RE.match(token):
            if in_target:
                # A new date after the target closes the target date block.
                break
            in_target = token == target
            saw_target = saw_target or in_target
            continue
        if in_target and TIME_RE.match(token):
            times.append(token.upper())
    return times if saw_target else []


def parse_tikus_times(html: str, show_date: str) -> list[str]:
    """Extract TIKUS! times for one date from one official cinema page.

    The parser is deliberately conservative. If multiple title occurrences
    exist, it returns the first bounded TIKUS! section that actually contains
    the requested date. It never scans unbounded into another movie card.
    """
    tokens = _tokens(html)
    target = datetime.strptime(show_date, "%Y-%m-%d").strftime("%A, %d %B %Y")
    for section in _candidate_sections(tokens):
        times = _times_from_section(section, target)
        if times:
            # Preserve page order while removing accidental duplicate links.
            return list(dict.fromkeys(times))
    return []


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
