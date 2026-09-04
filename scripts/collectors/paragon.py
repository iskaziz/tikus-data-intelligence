"""Paragon schedule-only collector boundary.

The two cinema codes are canonical, but the currently proven public flow did
not expose trustworthy seat counts without entering booking pages. This
adapter therefore returns no invented observations. Legacy verified schedules
may be imported separately with provenance.
"""
from scripts.collectors.base import Collector


class ParagonCollector(Collector):
    exhibitor_id = "paragon"

    def collect(self, show_date: str):
        return []
