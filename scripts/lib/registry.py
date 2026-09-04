from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def cinemas() -> list[dict]:
    return json.loads((ROOT / "data/meta/cinemas.json").read_text(encoding="utf-8"))["cinemas"]


def by_exhibitor(exhibitor_id: str) -> list[dict]:
    return [item for item in cinemas() if item["exhibitorId"] == exhibitor_id]


def by_source_id(exhibitor_id: str) -> dict[str, dict]:
    return {
        str(item["source"]["officialCinemaId"]): item
        for item in by_exhibitor(exhibitor_id)
        if item["source"].get("officialCinemaId") is not None
    }
