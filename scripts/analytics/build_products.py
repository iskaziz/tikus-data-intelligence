#!/usr/bin/env python3
"""Build browser-facing current/day products from immutable normalized history."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable
from zoneinfo import ZoneInfo

from scripts.analytics.metrics import aggregate, cinema_rankings, seat_state_velocity

TZ = ZoneInfo("Asia/Kuala_Lumpur")


def _read_snapshots(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("snapshots"), list):
        return payload["snapshots"]
    if isinstance(payload, dict) and payload.get("sessionId"):
        return [payload]
    return []


def load_history(root: Path) -> list[dict]:
    snapshots: list[dict] = []
    for path in sorted((root / "data/history").glob("*/*.json")):
        snapshots.extend(_read_snapshots(path))
    return snapshots


def load_corrections(root: Path) -> list[dict]:
    path = root / "data/meta/corrections.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [x for x in payload.get("corrections", []) if x.get("status") == "active"]


def _matches_correction(item: dict, correction: dict) -> bool:
    match = correction.get("match", {})
    if match.get("cinemaId") and item.get("cinemaId") != match["cinemaId"]:
        return False
    if match.get("showDates") and item.get("showDate") not in match["showDates"]:
        return False
    version = (item.get("source") or {}).get("collectorVersion")
    if match.get("collectorVersions") and version not in match["collectorVersions"]:
        return False
    if match.get("sessionIds") and item.get("sessionId") not in match["sessionIds"]:
        return False
    return True


def apply_corrections(snapshots: list[dict], corrections: list[dict]) -> tuple[list[dict], list[dict]]:
    included=[]; excluded=[]
    for item in snapshots:
        matched=[c for c in corrections if c.get("action") == "exclude-from-analytics" and _matches_correction(item, c)]
        if matched:
            excluded.append({"sessionId": item.get("sessionId"), "collectedAt": item.get("collectedAt"), "correctionIds": [c["id"] for c in matched]})
        else:
            included.append(item)
    return included, excluded


def latest_by_session(snapshots: Iterable[dict], *, as_of: datetime | None = None, pre_show_only: bool = False) -> list[dict]:
    latest: dict[str, dict] = {}
    for item in snapshots:
        collected = datetime.fromisoformat(item["collectedAt"])
        if as_of and collected > as_of:
            continue
        if pre_show_only and collected > datetime.fromisoformat(item["startAt"]):
            continue
        previous = latest.get(item["sessionId"])
        if previous is None or collected > datetime.fromisoformat(previous["collectedAt"]):
            latest[item["sessionId"]] = item
    return list(latest.values())


def grouped_summary(snapshots: list[dict], key: str) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in snapshots:
        grouped[item[key]].append(item)
    return [{key: group_key, **aggregate(items)} for group_key, items in sorted(grouped.items())]


def session_series(snapshots: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in snapshots:
        grouped[item["sessionId"]].append(item)
    result: dict[str, list[dict]] = {}
    for sid, items in grouped.items():
        items = sorted(items, key=lambda x: x["collectedAt"])
        result[sid] = [
            {
                "collectedAt": x["collectedAt"],
                "capacity": x["seat"].get("capacity"),
                "used": x["seat"].get("used"),
                "available": x["seat"].get("available"),
                "otherUnavailable": x["seat"].get("otherUnavailable"),
                "seatMeasured": x["quality"].get("seatMeasured", False),
            }
            for x in items
        ]
    return result


def session_changes(snapshots: list[dict]) -> dict[str, dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in snapshots:
        grouped[item["sessionId"]].append(item)
    result: dict[str, dict] = {}
    for sid, items in grouped.items():
        measured = [x for x in sorted(items, key=lambda x: x["collectedAt"]) if x["quality"].get("seatMeasured")]
        if len(measured) < 2:
            result[sid] = {"usedDelta": None, "hours": None, "seatsPerHour": None, "previousCollectedAt": None}
            continue
        previous, current = measured[-2], measured[-1]
        try:
            delta = seat_state_velocity(previous, current)
            result[sid] = {**delta, "previousCollectedAt": previous["collectedAt"]}
        except ValueError:
            result[sid] = {"usedDelta": None, "hours": None, "seatsPerHour": None, "previousCollectedAt": None}
    return result


def _state_summaries(root: Path, latest: list[dict]) -> list[dict]:
    registry = json.loads((root / "data/meta/cinemas.json").read_text(encoding="utf-8"))
    state_by_cinema = {c["id"]: c["state"] for c in registry["cinemas"]}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in latest:
        state = state_by_cinema.get(item["cinemaId"])
        if state:
            grouped[state].append(item)
    return [{"state": state, **aggregate(items)} for state, items in sorted(grouped.items())]


def live_upcoming_sessions(snapshots: list[dict], *, as_of: datetime) -> list[dict]:
    """Latest observed sessions that have not started by the analytical as-of time.

    This intentionally excludes schedule residue first observed only after a show
    has already started. Daily products still retain those observations for audit.
    """
    latest = latest_by_session(snapshots, as_of=as_of)
    return [x for x in latest if datetime.fromisoformat(x["startAt"]) >= as_of]


def final_pre_show_sessions(snapshots: list[dict], *, as_of: datetime) -> tuple[list[dict], dict]:
    """Return final pre-show snapshots only for sessions whose start time has passed.

    Before a session starts, its final pre-show observation is unknowable and is
    therefore excluded rather than represented by the latest provisional value.
    """
    latest = latest_by_session(snapshots, as_of=as_of)
    started = [x for x in latest if datetime.fromisoformat(x["startAt"]) <= as_of]
    started_ids = {x["sessionId"] for x in started}
    eligible_history = [x for x in snapshots if x["sessionId"] in started_ids]
    finals = latest_by_session(eligible_history, as_of=as_of, pre_show_only=True)
    final_ids = {x["sessionId"] for x in finals}
    missing = sorted(started_ids - final_ids)
    latest_ids = {x["sessionId"] for x in latest}
    future_ids = latest_ids - started_ids
    status = "complete" if latest_ids and not future_ids and not missing else ("provisional" if latest_ids else "no-observations")
    return finals, {
        "status": status,
        "startedSessions": len(started_ids),
        "futureSessions": len(future_ids),
        "finalizedSessions": len(final_ids),
        "missingFinalPreShowSessionIds": missing,
    }


def first_seen_after_show(snapshots: list[dict]) -> list[str]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in snapshots:
        grouped[item["sessionId"]].append(item)
    flagged: list[str] = []
    for sid, items in grouped.items():
        first = min(items, key=lambda x: x["collectedAt"])
        if datetime.fromisoformat(first["collectedAt"]) > datetime.fromisoformat(first["startAt"]):
            flagged.append(sid)
    return sorted(flagged)


def latest_run_for_date(root: Path, show_date: str) -> dict | None:
    matches=[]
    for path in (root / "data/runs").glob("*.json"):
        try:
            payload=json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if payload.get("showDate") == show_date:
            matches.append(payload)
    return max(matches, key=lambda x: x.get("collectedAt") or "") if matches else None


def build_day_product(root: Path, show_date: str, snapshots: list[dict], *, excluded: list[dict] | None = None) -> dict:
    day = [x for x in snapshots if x["showDate"] == show_date]
    generated_at = datetime.now(TZ)
    latest = latest_by_session(day)
    final_pre_show, final_state = final_pre_show_sessions(day, as_of=generated_at)
    live = live_upcoming_sessions(day, as_of=generated_at) if show_date == generated_at.date().isoformat() else []
    summary = aggregate(latest)
    final_summary = aggregate(final_pre_show)
    live_summary = aggregate(live)
    collected_times = sorted(x["collectedAt"] for x in day)
    flagged = first_seen_after_show(day)
    latest_run = latest_run_for_date(root, show_date)
    return {
        "schemaVersion": "1.3.0",
        "generatedAt": generated_at.isoformat(timespec="seconds"),
        "filmId": "tikus",
        "showDate": show_date,
        "status": "ok" if latest else "no-observations",
        "scope": {
            "cinemaCount": 16,
            "seatMeasuredSessions": summary["seatMeasuredSessions"],
            "totalSessions": summary["totalShows"],
            "liveUpcomingSessions": live_summary["totalShows"],
            "finalizedPreShowSessions": final_state["finalizedSessions"],
        },
        "summary": summary,
        "liveSummary": live_summary,
        "finalPreShowSummary": final_summary,
        "finalPreShowState": final_state,
        "cinemas": cinema_rankings(latest),
        "sessions": sorted(latest, key=lambda x: (x["startAt"], x["cinemaId"])),
        "liveSessions": sorted(live, key=lambda x: (x["startAt"], x["cinemaId"])),
        "finalPreShowSessions": sorted(final_pre_show, key=lambda x: (x["startAt"], x["cinemaId"])),
        "sessionChanges": session_changes(day),
        "series": session_series(day),
        "exhibitors": grouped_summary(latest, "exhibitorId"),
        "states": _state_summaries(root, latest),
        "observationWindow": {
            "firstCollectedAt": collected_times[0] if collected_times else None,
            "lastCollectedAt": collected_times[-1] if collected_times else None,
            "observations": len(day),
        },
        "collection": {
            "latestRun": latest_run,
            "firstSeenAfterShowSessionIds": flagged,
            "firstSeenAfterShowCount": len(flagged),
            "dailyCompleteness": "partial" if flagged or not day else "observed",
            "note": "Daily totals reflect sessions actually observed by this repository. A collector started late in the theatrical day cannot reconstruct earlier sessions from sources that return upcoming inventory only.",
        },
        "quality": {
            "seatCoverage": summary["seatCoverage"],
            "methodology": "docs/METHODOLOGY.md",
            "observedSeatStateIsNotSales": True,
            "excludedObservationCount": len(excluded or []),
            "correctionsApplied": sorted({cid for e in (excluded or []) for cid in e.get("correctionIds", [])}),
        },
    }


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_all_products(root: Path) -> None:
    raw_snapshots = load_history(root)
    corrections = load_corrections(root)
    snapshots, excluded = apply_corrections(raw_snapshots, corrections)
    dates = sorted({x["showDate"] for x in raw_snapshots})
    products: dict[str, dict] = {}
    for show_date in dates:
        excluded_for_day = [x for x in excluded if any(r.get("sessionId") == x.get("sessionId") and r.get("showDate") == show_date for r in raw_snapshots)]
        product = build_day_product(root, show_date, snapshots, excluded=excluded_for_day)
        products[show_date] = product
        _write(root / "data/days" / f"{show_date}.json", product)

    if dates:
        latest_date = dates[-1]
        current = {**products[latest_date], "mode": "current"}
    else:
        current = {
            "schemaVersion": "1.3.0",
            "generatedAt": datetime.now(TZ).isoformat(timespec="seconds"),
            "filmId": "tikus",
            "showDate": None,
            "status": "no-observations",
            "scope": {"cinemaCount": 16, "seatMeasuredSessions": 0, "totalSessions": 0},
            "summary": aggregate([]),
            "liveSummary": aggregate([]),
            "finalPreShowSummary": aggregate([]),
            "finalPreShowState": {"status":"no-observations","startedSessions":0,"futureSessions":0,"finalizedSessions":0,"missingFinalPreShowSessionIds":[]},
            "cinemas": [], "sessions": [], "liveSessions": [], "finalPreShowSessions": [], "sessionChanges": {}, "series": {},
            "exhibitors": [], "states": [],
            "observationWindow": {"firstCollectedAt": None, "lastCollectedAt": None, "observations": 0},
            "collection": {"latestRun": None, "firstSeenAfterShowSessionIds": [], "firstSeenAfterShowCount": 0, "dailyCompleteness": "no-observations", "note": None},
            "quality": {"seatCoverage": None, "methodology": "docs/METHODOLOGY.md", "observedSeatStateIsNotSales": True, "excludedObservationCount": 0, "correctionsApplied": []},
            "mode": "current",
        }
    _write(root / "data/current.json", current)
    _write(root / "data/index.json", {
        "schemaVersion": "1.0.0",
        "generatedAt": datetime.now(TZ).isoformat(timespec="seconds"),
        "availableDates": dates,
        "latestDate": dates[-1] if dates else None,
        "releaseDate": "2026-09-03",
    })

    # Latest collector-run status is separate from analytical data.
    run_paths = sorted((root / "data/runs").glob("*.json"))
    latest_run = json.loads(run_paths[-1].read_text(encoding="utf-8")) if run_paths else None
    status_payload = {
        "schemaVersion": "1.0.0",
        "generatedAt": datetime.now(TZ).isoformat(timespec="seconds"),
        "latestRun": latest_run,
        "historyFiles": len(list((root / "data/history").glob("*/*.json"))),
        "availableDates": dates,
    }
    _write(root / "data/status.json", status_payload)

    # Classic-script mirror keeps the static dashboard usable through file://.
    # JSON remains the canonical browser-facing data layer on hosted HTTP.
    browser_data = {
        "current": current,
        "index": json.loads((root / "data/index.json").read_text(encoding="utf-8")),
        "cinemas": json.loads((root / "data/meta/cinemas.json").read_text(encoding="utf-8")),
        "exhibitors": json.loads((root / "data/meta/exhibitors.json").read_text(encoding="utf-8")),
        "methodology": json.loads((root / "data/meta/methodology.json").read_text(encoding="utf-8")),
        "status": status_payload,
        "days": products,
    }
    js = "window.TIKUS_BROWSER_DATA = " + json.dumps(browser_data, ensure_ascii=False, separators=(",", ":")) + ";\n"
    (root / "data/browser-data.js").write_text(js, encoding="utf-8")


if __name__ == "__main__":
    build_all_products(Path(__file__).resolve().parents[2])
