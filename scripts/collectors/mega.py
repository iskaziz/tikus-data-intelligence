"""Read-only Mega Cineplex schedule collector for TIKUS! at Riverfront.

Reads the official TIKUS! movie-details page. No ticketing or seat-selection
flow is opened, and no capacity is inferred.
"""
from __future__ import annotations

import re
from datetime import datetime
from html.parser import HTMLParser

from scripts.collectors.base import Collector
from scripts.lib.http import get

COLLECTOR_VERSION = "mega-schedule/1.0.0"
MOVIE_URL = "https://www.megacineplex.com.my/Movies/Details?id=3788"
DATE_RE = re.compile(r"^(\d{2})\s+([A-Z]{3})\s+\([A-Z]+\)$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.I)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts=[]
    def handle_data(self, data: str):
        text = " ".join(data.split())
        if text: self.parts.append(text)


def _tokens(html: str) -> list[str]:
    p = _Text(); p.feed(html); return p.parts


def parse_riverfront_times(html: str, show_date: str) -> list[str]:
    tokens = _tokens(html)
    try:
        start = next(i for i,t in enumerate(tokens) if "riverfront" in t.casefold() and "sungai petani" in t.casefold())
    except StopIteration:
        return []
    dt = datetime.strptime(show_date, "%Y-%m-%d")
    target = dt.strftime("%d %b").upper()
    in_target = False
    times=[]
    for token in tokens[start+1:]:
        m = DATE_RE.match(token.upper())
        if m:
            date_prefix = f"{m.group(1)} {m.group(2)}"
            if in_target: break
            in_target = date_prefix == target
            continue
        if in_target and TIME_RE.match(token):
            times.append(token.upper())
    return times


def to_24h(value: str) -> str:
    return datetime.strptime(value, "%I:%M %p").strftime("%H:%M")


class MegaCollector(Collector):
    exhibitor_id = "mega"

    def collect(self, show_date: str):
        response = get(MOVIE_URL)
        return [{
            "cinemaId": "mega-riverfront-mall",
            "sourceCinemaId": "riverfront-sungai-petani",
            "sourceCinemaName": "Riverfront, Sungai Petani",
            "showDate": show_date,
            "session": {"time": to_24h(t), "format": None, "language": "Malay"},
            "scheduleUrl": MOVIE_URL,
            "schedulePayloadHash": response.sha256,
            "errors": [],
        } for t in parse_riverfront_times(response.text, show_date)]
