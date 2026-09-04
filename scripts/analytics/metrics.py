"""Pure calculation helpers for TIKUS! Data Intelligence.

No network access and no source-specific parsing belongs here.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time
from typing import Iterable, Mapping, Any

PRIME_START = time(18, 0)
PRIME_END = time(21, 0)


def is_seat_measured(snapshot: Mapping[str, Any]) -> bool:
    seat = snapshot.get("seat", {})
    quality = snapshot.get("quality", {})
    return bool(
        quality.get("seatMeasured")
        and isinstance(seat.get("capacity"), int)
        and isinstance(seat.get("used"), int)
        and seat["capacity"] > 0
        and 0 <= seat["used"] <= seat["capacity"]
    )


def is_prime(snapshot: Mapping[str, Any]) -> bool:
    dt = datetime.fromisoformat(snapshot["startAt"])
    local_t = dt.timetz().replace(tzinfo=None)
    return PRIME_START <= local_t < PRIME_END


def safe_ratio(numerator: float | int | None, denominator: float | int | None):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def aggregate(snapshots: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    snapshots = list(snapshots)
    sessions = {}
    for snapshot in snapshots:
        previous = sessions.get(snapshot["sessionId"])
        if previous is None or datetime.fromisoformat(snapshot["collectedAt"]) > datetime.fromisoformat(previous["collectedAt"]):
            sessions[snapshot["sessionId"]] = snapshot
    latest = list(sessions.values())
    measured = [s for s in latest if is_seat_measured(s)]
    prime = [s for s in latest if is_prime(s)]
    prime_measured = [s for s in prime if is_seat_measured(s)]

    capacity = sum(s["seat"]["capacity"] for s in measured)
    used = sum(s["seat"]["used"] for s in measured)
    available_values = [s["seat"].get("available") for s in measured if isinstance(s["seat"].get("available"), int)]
    other_values = [s["seat"].get("otherUnavailable") for s in measured if isinstance(s["seat"].get("otherUnavailable"), int)]
    prime_capacity = sum(s["seat"]["capacity"] for s in prime_measured)
    prime_used = sum(s["seat"]["used"] for s in prime_measured)

    return {
        "totalShows": len(latest),
        "locationsWithConfirmedShows": len({s["cinemaId"] for s in latest}),
        "seatMeasuredSessions": len(measured),
        "observedCapacity": capacity if measured else None,
        "observedUsed": used if measured else None,
        "available": sum(available_values) if available_values else None,
        "otherUnavailable": sum(other_values) if other_values else None,
        "occupancy": safe_ratio(used, capacity),
        "averageUsedPerMeasuredSession": safe_ratio(used, len(measured)),
        "averageCapacityPerMeasuredSession": safe_ratio(capacity, len(measured)),
        "primeTimeShows": len(prime),
        "primeTimeOccupancy": safe_ratio(prime_used, prime_capacity),
        "seatCoverage": safe_ratio(len(measured), len(latest)),
    }


def cinema_rankings(snapshots: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    snapshots = list(snapshots)
    scope = aggregate(snapshots)
    scope_capacity = scope["observedCapacity"] or 0
    scope_used = scope["observedUsed"] or 0
    total_shows = scope["totalShows"]

    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot["cinemaId"]].append(snapshot)

    rows = []
    for cinema_id, items in grouped.items():
        metrics = aggregate(items)
        capacity = metrics["observedCapacity"]
        used = metrics["observedUsed"]
        show_share = safe_ratio(metrics["totalShows"], total_shows)
        seat_share = safe_ratio(capacity, scope_capacity)
        used_share = safe_ratio(used, scope_used)
        performance_index = safe_ratio(used_share, seat_share) if used_share is not None and seat_share is not None else None
        rows.append({
            "cinemaId": cinema_id,
            **metrics,
            "showShare": show_share,
            "seatShare": seat_share,
            "usedShare": used_share,
            "performanceIndex": performance_index,
        })

    return sorted(
        rows,
        key=lambda row: (
            row["observedUsed"] is not None,
            row["observedUsed"] if row["observedUsed"] is not None else -1,
            row["occupancy"] if row["occupancy"] is not None else -1,
        ),
        reverse=True,
    )


def seat_state_velocity(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
    if previous["sessionId"] != current["sessionId"]:
        raise ValueError("Velocity requires two observations of the same session")
    if not (is_seat_measured(previous) and is_seat_measured(current)):
        return {"usedDelta": None, "hours": None, "seatsPerHour": None}

    t1 = datetime.fromisoformat(previous["collectedAt"])
    t2 = datetime.fromisoformat(current["collectedAt"])
    hours = (t2 - t1).total_seconds() / 3600
    if hours <= 0:
        raise ValueError("Current observation must be later than previous observation")

    delta = current["seat"]["used"] - previous["seat"]["used"]
    return {"usedDelta": delta, "hours": hours, "seatsPerHour": delta / hours}
