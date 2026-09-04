"""Mega Cineplex schedule-only collector boundary.

Riverfront Mall remains in the tracked registry. No seat state is inferred.
The currently established source is a public listing rather than a seat API.
"""
from scripts.collectors.base import Collector


class MegaCollector(Collector):
    exhibitor_id = "mega"

    def collect(self, show_date: str):
        return []
