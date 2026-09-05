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
    if match.get("sourceSessionIds") and str(item.get("sourceSessionId")) not in {str(x) for x in match["sourceSessionIds"]}:
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



def reconcile_schedule_only_session_ids(snapshots: list[dict]) -> tuple[list[dict], list[dict]]:
    """Canonicalize duplicate schedule-only identities without mutating raw history.

    Legacy Paragon observations were fingerprinted by cinema/date/time while newer
    collectors preserve the exhibitor's native ticket-session ID. When both forms
    describe the same schedule-only screening, this analytical layer rewrites the
    legacy fingerprint to the native identity so the screening counts once.

    The reconciliation key is intentionally narrow: provider + cinema + show date +
    exact start time. Seat-measured observations are never rewritten here.
    """
    groups: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    passthrough: list[dict] = []
    for item in snapshots:
        if item.get("quality", {}).get("measurementStatus") != "schedule-only":
            passthrough.append(item)
            continue
        provider = (item.get("source") or {}).get("provider")
        key = (provider or "", item.get("cinemaId") or "", item.get("showDate") or "", item.get("startAt") or "")
        groups[key].append(item)

    reconciled = list(passthrough)
    audit: list[dict] = []
    for key, items in groups.items():
        native = [x for x in items if x.get("sourceSessionId") not in (None, "")]
        if native:
            # Prefer the newest native observation if multiple native IDs somehow
            # collide on the same exact screening key; retain all observations but
            # normalize their analytical sessionId to that canonical native ID.
            canonical_item = max(native, key=lambda x: x.get("collectedAt") or "")
            canonical_id = canonical_item.get("sessionId")
        else:
            canonical_item = max(items, key=lambda x: x.get("collectedAt") or "")
            canonical_id = canonical_item.get("sessionId")

        original_ids = sorted({x.get("sessionId") for x in items if x.get("sessionId")})
        changed = len(original_ids) > 1
        for item in items:
            if item.get("sessionId") == canonical_id:
                reconciled.append(item)
                continue
            clone = dict(item)
            clone["sessionId"] = canonical_id
            reconciled.append(clone)
        if changed:
            audit.append({
                "provider": key[0],
                "cinemaId": key[1],
                "showDate": key[2],
                "startAt": key[3],
                "canonicalSessionId": canonical_id,
                "mergedSessionIds": original_ids,
            })
    return reconciled, sorted(audit, key=lambda x: (x["startAt"], x["cinemaId"]))

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




def cinema_momentum(snapshots: list[dict]) -> list[dict]:
    """Recent observed seat-state change by cinema from the latest two measurements per session.

    This is deliberately not a ticket-sales metric. It uses source-defined observed
    used/booked seat states and only sessions with at least two valid measurements.
    """
    changes = session_changes(snapshots)
    grouped: dict[str, list[dict]] = defaultdict(list)
    latest = {x["sessionId"]: x for x in latest_by_session(snapshots)}
    for sid, change in changes.items():
        if change.get("usedDelta") is None or change.get("seatsPerHour") is None:
            continue
        item = latest.get(sid)
        if not item:
            continue
        grouped[item["cinemaId"]].append(change)
    rows=[]
    for cinema_id, items in grouped.items():
        rows.append({
            "cinemaId": cinema_id,
            "qualifyingSessions": len(items),
            "netUsedDelta": sum(x["usedDelta"] for x in items),
            "averageSeatsPerHour": sum(x["seatsPerHour"] for x in items) / len(items),
            "maxSeatsPerHour": max(x["seatsPerHour"] for x in items),
            "minSeatsPerHour": min(x["seatsPerHour"] for x in items),
        })
    return sorted(rows, key=lambda x: (x["averageSeatsPerHour"], x["netUsedDelta"]), reverse=True)


def prime_time_efficiency(snapshots: list[dict]) -> list[dict]:
    """Compare measured prime-time utilisation with each cinema's all-day utilisation."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in snapshots:
        grouped[item["cinemaId"]].append(item)
    rows=[]
    for cinema_id, items in grouped.items():
        all_summary = aggregate(items)
        prime = [x for x in items if "18:00" <= x["startAt"][11:16] < "21:00"]
        prime_summary = aggregate(prime)
        delta = None
        if prime_summary["occupancy"] is not None and all_summary["occupancy"] is not None:
            delta = prime_summary["occupancy"] - all_summary["occupancy"]
        rows.append({
            "cinemaId": cinema_id,
            "primeShows": prime_summary["totalShows"],
            "primeMeasuredSessions": prime_summary["seatMeasuredSessions"],
            "primeCapacity": prime_summary["observedCapacity"],
            "primeUsed": prime_summary["observedUsed"],
            "primeOccupancy": prime_summary["occupancy"],
            "allDayOccupancy": all_summary["occupancy"],
            "occupancyDelta": delta,
            "seatCoverage": prime_summary["seatCoverage"],
        })
    return sorted(rows, key=lambda x: (x["primeOccupancy"] is not None, x["primeOccupancy"] or -1), reverse=True)


def allocation_comparison(current: list[dict], previous: list[dict] | None, *, current_complete: str, previous_complete: str | None, previous_date: str | None) -> dict:
    """Observed schedule-allocation deltas between two day products.

    Deltas remain descriptive of repository-observed schedules. A comparison is
    marked limited whenever either day is partial, preventing partial acquisition
    from being presented as a definitive programming change.
    """
    if not previous or not previous_date:
        return {"status":"unavailable","previousDate":previous_date,"quality":"no-previous-day","cinemas":[]}
    by_cur: dict[str,list[dict]] = defaultdict(list)
    by_prev: dict[str,list[dict]] = defaultdict(list)
    for x in current: by_cur[x["cinemaId"]].append(x)
    for x in previous: by_prev[x["cinemaId"]].append(x)
    ids=sorted(set(by_cur)|set(by_prev))
    rows=[]
    for cid in ids:
        cur=by_cur.get(cid,[]); prev=by_prev.get(cid,[])
        cur_prime=sum(1 for x in cur if "18:00" <= x["startAt"][11:16] < "21:00")
        prev_prime=sum(1 for x in prev if "18:00" <= x["startAt"][11:16] < "21:00")
        rows.append({
            "cinemaId":cid,
            "shows":len(cur),"previousShows":len(prev),"showDelta":len(cur)-len(prev),
            "primeShows":cur_prime,"previousPrimeShows":prev_prime,"primeShowDelta":cur_prime-prev_prime,
        })
    quality = "comparable" if current_complete == "observed" and previous_complete == "observed" else "limited-partial-day"
    return {"status":"ok","previousDate":previous_date,"quality":quality,"cinemas":rows}


def velocity_leaders(snapshots: list[dict], limit: int = 10) -> list[dict]:
    changes=session_changes(snapshots)
    latest={x["sessionId"]:x for x in latest_by_session(snapshots)}
    rows=[]
    for sid,c in changes.items():
        if c.get("seatsPerHour") is None: continue
        s=latest.get(sid)
        if not s: continue
        rows.append({"sessionId":sid,"cinemaId":s["cinemaId"],"startAt":s["startAt"],"usedDelta":c.get("usedDelta"),"hours":c.get("hours"),"seatsPerHour":c.get("seatsPerHour"),"previousCollectedAt":c.get("previousCollectedAt"),"latestCollectedAt":s.get("collectedAt")})
    return sorted(rows,key=lambda x:x["seatsPerHour"],reverse=True)[:limit]



def decision_intelligence(latest: list[dict], momentum: list[dict], prime_efficiency: list[dict], allocation_cmp: dict, *, daily_completeness: str) -> dict:
    """Derive cautious operational review signals from observed seat-state evidence.

    These are triage signals, not forecasts or sales recommendations. They only use
    corrected/reconciled analytical observations and preserve the repository's
    distinction between observed seat state and paid admissions.
    """
    rankings = {r["cinemaId"]: r for r in cinema_rankings(latest)}
    momentum_by = {r["cinemaId"]: r for r in momentum}
    prime_by = {r["cinemaId"]: r for r in prime_efficiency}
    alloc_by = {r["cinemaId"]: r for r in (allocation_cmp.get("cinemas") or [])}
    network = aggregate(latest)
    network_occ = network.get("occupancy")
    rows = []

    for cinema_id, rank in rankings.items():
        if not rank.get("seatMeasuredSessions"):
            continue
        m = momentum_by.get(cinema_id, {})
        p = prime_by.get(cinema_id, {})
        a = alloc_by.get(cinema_id, {})
        evidence = []
        positive = 0
        caution = 0

        pi = rank.get("performanceIndex")
        occ = rank.get("occupancy")
        avg_vel = m.get("averageSeatsPerHour")
        q_sessions = m.get("qualifyingSessions") or 0
        prime_delta = p.get("occupancyDelta")
        prime_measured = p.get("primeMeasuredSessions") or 0

        if pi is not None and pi >= 1.25 and (rank.get("observedUsed") or 0) >= 2:
            positive += 1
            evidence.append(f"Seat-State Performance Index {pi:.2f}×")
        elif pi is not None and pi <= 0.75 and rank.get("observedCapacity"):
            caution += 1
            evidence.append(f"Seat-State Performance Index {pi:.2f}×")

        if avg_vel is not None and q_sessions:
            if avg_vel > 0.25:
                positive += 1
                evidence.append(f"recent momentum +{avg_vel:.1f} observed seats/hr")
            elif avg_vel < -0.25:
                caution += 1
                evidence.append(f"recent momentum {avg_vel:.1f} observed seats/hr")

        if prime_delta is not None and prime_measured:
            if prime_delta >= 0.005:
                positive += 1
                evidence.append(f"prime utilisation +{prime_delta*100:.2f} pp vs all-day")
            elif prime_delta <= -0.005:
                caution += 1
                evidence.append(f"prime utilisation {prime_delta*100:.2f} pp vs all-day")

        if allocation_cmp.get("quality") == "comparable" and a:
            delta = a.get("showDelta") or 0
            if delta < 0 and positive >= 1:
                evidence.append(f"observed allocation down {abs(delta)} show(s) vs prior day")
            elif delta > 0 and caution >= 1:
                evidence.append(f"observed allocation up {delta} show(s) vs prior day")

        signal = "monitor"
        label = "Monitor"
        rationale = "No strong allocation-fit signal from the current observed evidence."
        if positive >= 2 and caution == 0:
            signal = "review-opportunity"
            label = "Review opportunity"
            rationale = "Multiple observed indicators are outperforming relative to the measured network; review whether current allocation remains proportionate."
        elif caution >= 2 and positive == 0:
            signal = "capacity-watch"
            label = "Capacity watch"
            rationale = "Multiple observed indicators are underperforming relative to the measured network; review utilisation before expanding allocation."
        elif positive >= 1 and caution >= 1:
            signal = "mixed"
            label = "Mixed signal"
            rationale = "Observed indicators disagree; avoid making an allocation inference from a single metric."

        confidence = "low"
        if q_sessions >= 2 and rank.get("seatCoverage") == 1.0:
            confidence = "medium"
        if daily_completeness != "observed":
            confidence = "low"

        rows.append({
            "cinemaId": cinema_id,
            "signal": signal,
            "label": label,
            "confidence": confidence,
            "rationale": rationale,
            "evidence": evidence[:4],
            "performanceIndex": pi,
            "occupancy": occ,
            "networkOccupancy": network_occ,
            "averageSeatsPerHour": avg_vel,
            "primeOccupancyDelta": prime_delta,
            "showDelta": a.get("showDelta") if a else None,
        })

    priority = {"review-opportunity": 0, "mixed": 1, "capacity-watch": 2, "monitor": 3}
    rows.sort(key=lambda r: (priority.get(r["signal"], 9), -(r.get("performanceIndex") or 0), r["cinemaId"]))
    counts = {k: sum(1 for r in rows if r["signal"] == k) for k in ("review-opportunity", "mixed", "capacity-watch", "monitor")}
    return {
        "status": "ok" if rows else "unavailable",
        "quality": "provisional-live-observation" if daily_completeness != "observed" else "observed-day",
        "networkOccupancy": network_occ,
        "counts": counts,
        "cinemas": rows,
        "definition": "Operational review signals derived from observed seat-state performance, repeated-measurement momentum and prime-time utilisation. They are not forecasts, ticket-sales estimates or automated allocation recommendations.",
    }

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


def build_day_product(root: Path, show_date: str, snapshots: list[dict], *, excluded: list[dict] | None = None, reconciliations: list[dict] | None = None) -> dict:
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
    momentum = cinema_momentum(day)
    prime_efficiency = prime_time_efficiency(latest)
    velocity = velocity_leaders(day)
    daily_completeness = "partial" if flagged or not day else "observed"
    return {
        "schemaVersion": "1.5.0",
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
        "intelligence": {
            "cinemaMomentum": momentum,
            "primeTimeEfficiency": prime_efficiency,
            "sessionVelocityLeaders": velocity,
            "allocationComparison": {"status":"pending-build","previousDate":None,"quality":"not-evaluated","cinemas":[]},
            "decisionSignals": {"status":"pending-build","quality":"not-evaluated","counts":{},"cinemas":[],"definition":""},
            "definitions": {
                "momentum": "Latest observed seat-state change across sessions with at least two valid measurements. Not paid ticket sales.",
                "primeTimeEfficiency": "Capacity-weighted observed utilisation for sessions starting 18:00 inclusive to 21:00 exclusive, compared with all-day utilisation.",
                "allocationComparison": "Observed schedule-count change versus the previous available day; limited when either day is partial.",
                "decisionSignals": "Cautious operational review signals derived from relative observed seat-state performance, repeated-measurement momentum and prime-time utilisation; not forecasts or sales recommendations."
            }
        },
        "observationWindow": {
            "firstCollectedAt": collected_times[0] if collected_times else None,
            "lastCollectedAt": collected_times[-1] if collected_times else None,
            "observations": len(day),
        },
        "collection": {
            "latestRun": latest_run,
            "firstSeenAfterShowSessionIds": flagged,
            "firstSeenAfterShowCount": len(flagged),
            "dailyCompleteness": daily_completeness,
            "note": "Daily totals reflect sessions actually observed by this repository. A collector started late in the theatrical day cannot reconstruct earlier sessions from sources that return upcoming inventory only.",
        },
        "quality": {
            "seatCoverage": summary["seatCoverage"],
            "methodology": "docs/METHODOLOGY.md",
            "observedSeatStateIsNotSales": True,
            "excludedObservationCount": len(excluded or []),
            "correctionsApplied": sorted({cid for e in (excluded or []) for cid in e.get("correctionIds", [])}),
            "sessionIdentityReconciliations": len(reconciliations or []),
            "reconciledSessions": reconciliations or [],
        },
    }


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_all_products(root: Path) -> None:
    raw_snapshots = load_history(root)
    corrections = load_corrections(root)
    snapshots, excluded = apply_corrections(raw_snapshots, corrections)
    snapshots, reconciliation_audit = reconcile_schedule_only_session_ids(snapshots)
    dates = sorted({x["showDate"] for x in raw_snapshots})
    products: dict[str, dict] = {}
    for index, show_date in enumerate(dates):
        excluded_for_day = [x for x in excluded if any(r.get("sessionId") == x.get("sessionId") and r.get("showDate") == show_date for r in raw_snapshots)]
        reconciliations_for_day = [x for x in reconciliation_audit if x.get("showDate") == show_date]
        product = build_day_product(root, show_date, snapshots, excluded=excluded_for_day, reconciliations=reconciliations_for_day)
        previous_date = dates[index-1] if index else None
        previous_product = products.get(previous_date) if previous_date else None
        product["intelligence"]["allocationComparison"] = allocation_comparison(
            product.get("sessions", []),
            previous_product.get("sessions", []) if previous_product else None,
            current_complete=product.get("collection", {}).get("dailyCompleteness"),
            previous_complete=previous_product.get("collection", {}).get("dailyCompleteness") if previous_product else None,
            previous_date=previous_date,
        )
        product["intelligence"]["decisionSignals"] = decision_intelligence(
            product.get("sessions", []),
            product.get("intelligence", {}).get("cinemaMomentum", []),
            product.get("intelligence", {}).get("primeTimeEfficiency", []),
            product.get("intelligence", {}).get("allocationComparison", {}),
            daily_completeness=product.get("collection", {}).get("dailyCompleteness") or "partial",
        )
        products[show_date] = product
        _write(root / "data/days" / f"{show_date}.json", product)

    if dates:
        latest_date = dates[-1]
        current = {**products[latest_date], "mode": "current"}
    else:
        current = {
            "schemaVersion": "1.5.0",
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
            "intelligence": {"cinemaMomentum":[],"primeTimeEfficiency":[],"sessionVelocityLeaders":[],"allocationComparison":{"status":"unavailable","previousDate":None,"quality":"no-previous-day","cinemas":[]},"decisionSignals":{"status":"unavailable","quality":"no-observations","counts":{},"cinemas":[],"definition":""},"definitions":{}},
            "observationWindow": {"firstCollectedAt": None, "lastCollectedAt": None, "observations": 0},
            "collection": {"latestRun": None, "firstSeenAfterShowSessionIds": [], "firstSeenAfterShowCount": 0, "dailyCompleteness": "no-observations", "note": None},
            "quality": {"seatCoverage": None, "methodology": "docs/METHODOLOGY.md", "observedSeatStateIsNotSales": True, "excludedObservationCount": 0, "correctionsApplied": [], "sessionIdentityReconciliations": 0, "reconciledSessions": []},
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
