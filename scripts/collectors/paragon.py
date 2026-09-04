"""Read-only Paragon schedule collector.

Paragon/Vista cinema pages contain many movie cards and may repeat a film title
outside its schedule card.  v1.2 parses the HTML tree and selects the *smallest
ancestor element* that contains both the exact TIKUS! title and Vista's
"Future Dates" schedule marker.  Date/time extraction is then limited to that
single subtree, preventing neighbouring movie times from leaking in.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser

from scripts.collectors.base import Collector
from scripts.lib.http import get
from scripts.lib.registry import by_exhibitor

COLLECTOR_VERSION = "paragon-schedule/1.2.0"
BASE = "https://www.paragoncinemas.com.my/Browsing/Cinemas/Details/{code}"
DATE_RE = re.compile(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s+(\d{2})\s+([A-Za-z]+)\s+(\d{4})$")
TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*(AM|PM)$", re.I)

@dataclass
class Node:
    tag: str
    parent: "Node | None" = None
    children: list["Node | str"] = field(default_factory=list)

class TreeParser(HTMLParser):
    VOID = {"area","base","br","col","embed","hr","img","input","link","meta","param","source","track","wbr"}
    def __init__(self):
        super().__init__()
        self.root = Node("document")
        self.stack = [self.root]
    def handle_starttag(self, tag, attrs):
        node = Node(tag, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)
    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, self.stack[-1]))
    def handle_endtag(self, tag):
        for i in range(len(self.stack)-1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return
    def handle_data(self, data):
        text = " ".join(data.split())
        if text:
            self.stack[-1].children.append(text)

def _texts(node: Node) -> list[str]:
    out=[]
    def walk(n):
        for child in n.children:
            if isinstance(child, str): out.append(child)
            else: walk(child)
    walk(node)
    return out

def _nodes(node: Node):
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from _nodes(child)

def _is_tikus_card(node: Node) -> bool:
    texts=_texts(node)
    exact_title=any(t.strip().casefold()=="tikus!" for t in texts)
    schedule_marker=any("future dates" in t.casefold() for t in texts)
    return exact_title and schedule_marker

def _card_for_tikus(html: str) -> Node | None:
    parser=TreeParser(); parser.feed(html)
    candidates=[n for n in _nodes(parser.root) if n.tag not in {"document","html","body"} and _is_tikus_card(n)]
    if not candidates:
        return None
    # Smallest text-bearing subtree is the nearest shared ancestor of title + schedule.
    return min(candidates, key=lambda n: len(_texts(n)))

def parse_tikus_times(html: str, show_date: str) -> list[str]:
    card=_card_for_tikus(html)
    if card is None:
        return []
    target=datetime.strptime(show_date, "%Y-%m-%d").strftime("%A, %d %B %Y")
    in_target=False; saw_target=False; times=[]
    for token in _texts(card):
        if DATE_RE.match(token):
            if in_target:
                break
            in_target = token == target
            saw_target = saw_target or in_target
            continue
        if in_target and TIME_RE.match(token):
            times.append(token.upper())
    return list(dict.fromkeys(times)) if saw_target else []

def to_24h(value: str) -> str:
    return datetime.strptime(value, "%I:%M %p").strftime("%H:%M")

class ParagonCollector(Collector):
    exhibitor_id = "paragon"
    def collect(self, show_date: str):
        facts=[]
        for cinema in by_exhibitor("paragon"):
            code=cinema.get("source",{}).get("officialCinemaId")
            if not code: continue
            url=BASE.format(code=code); response=get(url)
            for time_text in parse_tikus_times(response.text, show_date):
                facts.append({
                    "cinemaId": cinema["id"], "sourceCinemaId": code,
                    "sourceCinemaName": cinema.get("name"), "showDate": show_date,
                    "session": {"time": to_24h(time_text), "format":"2D", "language":"Malay"},
                    "scheduleUrl": url, "schedulePayloadHash": response.sha256, "errors": [],
                })
        return facts
