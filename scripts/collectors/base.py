"""Collector contract.

Collectors acquire source facts only. They must not calculate dashboard metrics,
and they must never perform seat-selection or booking actions.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Collector(ABC):
    exhibitor_id: str

    @abstractmethod
    def collect(self, show_date: str) -> list[dict[str, Any]]:
        """Return source-native facts for normalization."""
        raise NotImplementedError
