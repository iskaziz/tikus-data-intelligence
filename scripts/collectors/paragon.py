"""Read-only Paragon schedule collector.

v1.3 uses Paragon/Vista link semantics as the structural contract:
- movie titles are anchors under /Browsing/Movies/Details/
- showtimes are anchors under /Ticketing/visSelectTickets.aspx

The parser starts at the exact TIKUS! movie-title anchor and stops at the next
movie-title anchor. Only ticketing anchors inside that segment are considered.
This avoids both prior failure modes: stray TIKUS! text leaking neighbouring
showtimes (v1.1) and over-strict ancestor matching returning no sessions (v1.2).
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

from scripts.collectors.base import Collector
from scripts.lib.http import get
from scripts.lib.registry import by_exhibitor

COLLECTOR_VERSION = "paragon-schedule/1.3.0"
BASE = "https://www.paragoncinemas.com.my/Browsing/Cinemas/Details/{code}"
DATE_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(\d{2})\s+([A-Za-z]+)\s+(\d{4})$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.I)
MOVIE_PATH = "/browsing/movies/details/"
TICKET_PATH = "/ticketing/visselecttickets.aspx"


@dataclass
class Event:
    kind: str
    text: str = ""
    href: str | None = None
    tag: str | None = None


class EventParser(HTMLParser):
    """Flatten HTML to ordered text/anchor events while preserving hrefs."""

    def __init__(self):
        super().__init__()
        self.events: list[Event] = []
        self._anchor_href: str | None = None
        self._anchor_text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            self._anchor_href = dict(attrs).get("href")
            self._anchor_text = []

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._anchor_href is not None:
            text = " ".join(self._anchor_text).strip()
            self.events.append(Event("anchor", text=text, href=self._anchor_href, tag="a"))
            self._anchor_href = None
            self._anchor_text = []

    def handle_data(self, data):
        text = " ".join(data.split()).strip()
        if not text:
            return
        if self._anchor_href is not None:
            self._anchor_text.append(text)
        else:
            self.events.append(Event("text", text=text))


def _path(href: str | None) -> str:
    if not href:
        return ""
    try:
        return urlparse(href).path.casefold()
    except Exception:
        return ""


def _is_movie_anchor(event: Event) -> bool:
    return event.kind == "anchor" and MOVIE_PATH in _path(event.href)


def _is_tikus_anchor(event: Event) -> bool:
    return _is_movie_anchor(event) and event.text.strip().casefold() == "tikus!"


def _is_ticket_anchor(event: Event) -> bool:
    return event.kind == "anchor" and TICKET_PATH in _path(event.href)


def _session_id(href: str | None) -> str | None:
    if not href:
        return None
    try:
        values = parse_qs(urlparse(href).query)
        ids = values.get("txtSessionId") or values.get("txtsessionid")
        return ids[0] if ids else None
    except Exception:
        return None


def parse_tikus_schedule(html: str, show_date: str) -> tuple[list[dict], dict]:
    parser = EventParser()
    parser.feed(html)
    events = parser.events

    title_indexes = [i for i, event in enumerate(events) if _is_movie_anchor(event)]
    tikus_indexes = [i for i in title_indexes if _is_tikus_anchor(events[i])]
    target = datetime.strptime(show_date, "%Y-%m-%d").strftime("%A, %d %B %Y")

    diagnostics = {
        "movieTitleAnchors": len(title_indexes),
        "tikusTitleAnchors": len(tikus_indexes),
        "ticketAnchorsInTikusSegments": 0,
        "matchedDateTicketAnchors": 0,
        "rejectedTicketAnchors": 0,
        "rejectionReasons": {},
        "targetDate": target,
    }

    def reject(reason: str):
        diagnostics["rejectedTicketAnchors"] += 1
        diagnostics["rejectionReasons"][reason] = diagnostics["rejectionReasons"].get(reason, 0) + 1

    rows: list[dict] = []
    seen: set[tuple[str, str | None]] = set()

    for start in tikus_indexes:
        end = len(events)
        for idx in title_indexes:
            if idx > start:
                end = idx
                break

        current_date: str | None = None
        for event in events[start + 1:end]:
            if DATE_RE.match(event.text):
                current_date = event.text
                continue
            if not _is_ticket_anchor(event):
                continue

            diagnostics["ticketAnchorsInTikusSegments"] += 1
            if current_date != target:
                reject("ticket-anchor-outside-target-date")
                continue
            if not TIME_RE.match(event.text):
                reject("ticket-anchor-text-not-time")
                continue

            session_id = _session_id(event.href)
            key = (event.text.upper(), session_id)
            if key in seen:
                reject("duplicate-ticket-anchor")
                continue
            seen.add(key)
            diagnostics["matchedDateTicketAnchors"] += 1
            rows.append({
                "timeText": event.text.upper(),
                "sessionId": session_id,
                "ticketUrl": event.href,
            })

    if not tikus_indexes:
        diagnostics["rejectionReasons"]["no-exact-tikus-movie-anchor"] = 1
    elif diagnostics["ticketAnchorsInTikusSegments"] == 0:
        diagnostics["rejectionReasons"]["no-ticketing-anchors-in-tikus-segment"] = 1
    elif not rows:
        diagnostics["rejectionReasons"]["no-target-date-ticketing-anchors"] = 1

    return rows, diagnostics


def parse_tikus_times(html: str, show_date: str) -> list[str]:
    rows, _ = parse_tikus_schedule(html, show_date)
    return [row["timeText"] for row in rows]


def to_24h(value: str) -> str:
    return datetime.strptime(value, "%I:%M %p").strftime("%H:%M")


class ParagonCollector(Collector):
    exhibitor_id = "paragon"

    def __init__(self):
        self.diagnostics: dict[str, dict] = {}

    def collect(self, show_date: str):
        facts = []
        self.diagnostics = {}
        for cinema in by_exhibitor("paragon"):
            code = cinema.get("source", {}).get("officialCinemaId")
            if not code:
                continue
            url = BASE.format(code=code)
            response = get(url)
            rows, diagnostics = parse_tikus_schedule(response.text, show_date)
            diagnostics.update({
                "cinemaId": cinema["id"],
                "sourceCinemaId": code,
                "sourceUrl": url,
                "payloadHash": response.sha256,
                "parsedSessions": len(rows),
            })
            self.diagnostics[cinema["id"]] = diagnostics

            for row in rows:
                facts.append({
                    "cinemaId": cinema["id"],
                    "sourceCinemaId": code,
                    "sourceCinemaName": cinema.get("name"),
                    "showDate": show_date,
                    "sourceSessionId": row.get("sessionId"),
                    "session": {
                        "time": to_24h(row["timeText"]),
                        "format": "2D",
                        "language": "Malay",
                        "sessionId": row.get("sessionId"),
                    },
                    "scheduleUrl": url,
                    "ticketUrl": row.get("ticketUrl"),
                    "schedulePayloadHash": response.sha256,
                    "errors": [],
                })
        return facts
