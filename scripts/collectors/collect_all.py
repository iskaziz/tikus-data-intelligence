#!/usr/bin/env python3
"""Collect read-only public TIKUS! session facts and append normalized history."""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.collectors.gsc import GSCCollector, COLLECTOR_VERSION as GSC_VERSION
from scripts.collectors.tgv import TGVCollector, COLLECTOR_VERSION as TGV_VERSION
from scripts.collectors.paragon import ParagonCollector, COLLECTOR_VERSION as PARAGON_VERSION
from scripts.collectors.mega import MegaCollector, COLLECTOR_VERSION as MEGA_VERSION
from scripts.normalizers.schedule_only import normalize_schedule_only
from scripts.normalizers.gsc import normalize_gsc
from scripts.normalizers.tgv import normalize_tgv

ROOT = Path(__file__).resolve().parents[2]
TZ = ZoneInfo("Asia/Kuala_Lumpur")


def combined_hash(*parts: str | None) -> str | None:
    values = [p for p in parts if p]
    if not values:
        return None
    return hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()


def normalize_gsc_facts(facts: list[dict], *, run_id: str, collected_at: str) -> list[dict]:
    return [
        normalize_gsc(
            run_id=run_id,
            cinema_id=fact["cinemaId"],
            source_cinema_id=fact["sourceCinemaId"],
            source_cinema_name=fact["sourceCinemaName"],
            show_date=fact.get("showDate") or collected_at[:10],
            collected_at=collected_at,
            session=fact["session"],
            collector_version=GSC_VERSION,
            source_url=fact.get("seatStatusUrl") or fact.get("showtimesUrl"),
            raw_payload_hash=combined_hash(fact.get("showtimesPayloadHash"), fact.get("seatPayloadHash")),
            acquisition_warnings=fact.get("errors") or [],
        ) for fact in facts
    ]


def normalize_tgv_facts(facts: list[dict], *, run_id: str, collected_at: str) -> list[dict]:
    return [
        normalize_tgv(
            run_id=run_id,
            cinema_id=fact["cinemaId"],
            source_cinema_id=fact["sourceCinemaId"],
            source_cinema_name=fact["sourceCinemaName"],
            show_date=fact.get("showDate") or collected_at[:10],
            collected_at=collected_at,
            session=fact["session"],
            collector_version=TGV_VERSION,
            source_url=fact.get("seatStatusUrl") or fact.get("scheduleUrl"),
            raw_payload_hash=combined_hash(fact.get("schedulePayloadHash"), fact.get("seatPayloadHash")),
            acquisition_warnings=fact.get("errors") or [],
        ) for fact in facts
    ]


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Malaysia theatrical date, YYYY-MM-DD")
    parser.add_argument("--sources", default="gsc,tgv,paragon,mega", help="Comma separated: gsc,tgv,paragon,mega")
    parser.add_argument("--allow-empty", action="store_true", help="Do not fail when no sessions are found")
    args = parser.parse_args()

    now = datetime.now(TZ)
    show_date = args.date or now.date().isoformat()
    collected_at = now.isoformat(timespec="seconds")
    run_id = f"{now.strftime('%Y%m%dT%H%M%S%z')}-{uuid.uuid4().hex[:8]}"
    requested = {x.strip() for x in args.sources.split(",") if x.strip()}
    snapshots: list[dict] = []
    statuses: dict[str, dict] = {}

    if "gsc" in requested:
        try:
            facts = GSCCollector().collect(show_date)
            normalized = normalize_gsc_facts(facts, run_id=run_id, collected_at=collected_at)
            snapshots.extend(normalized)
            statuses["gsc"] = {
                "status": "ok", "snapshots": len(normalized),
                "seatMeasured": sum(1 for s in normalized if s["quality"]["seatMeasured"]),
            }
        except Exception as exc:
            statuses["gsc"] = {"status": "error", "snapshots": 0, "error": f"{type(exc).__name__}: {exc}"}

    if "tgv" in requested:
        try:
            facts = TGVCollector().collect(show_date)
            normalized = normalize_tgv_facts(facts, run_id=run_id, collected_at=collected_at)
            snapshots.extend(normalized)
            statuses["tgv"] = {
                "status": "ok", "snapshots": len(normalized),
                "seatMeasured": sum(1 for s in normalized if s["quality"]["seatMeasured"]),
            }
        except Exception as exc:
            statuses["tgv"] = {"status": "error", "snapshots": 0, "error": f"{type(exc).__name__}: {exc}"}


    if "paragon" in requested:
        try:
            facts = ParagonCollector().collect(show_date)
            normalized = [normalize_schedule_only(provider="paragon", exhibitor_id="paragon", run_id=run_id, cinema_id=f["cinemaId"], source_cinema_id=f.get("sourceCinemaId"), source_cinema_name=f.get("sourceCinemaName"), show_date=f["showDate"], collected_at=collected_at, session=f["session"], collector_version=PARAGON_VERSION, source_url=f.get("scheduleUrl"), raw_payload_hash=f.get("schedulePayloadHash"), acquisition_warnings=f.get("errors") or []) for f in facts]
            snapshots.extend(normalized)
            statuses["paragon"] = {"status": "ok-schedule-only", "snapshots": len(normalized), "seatMeasured": 0}
        except Exception as exc:
            statuses["paragon"] = {"status": "error", "snapshots": 0, "error": f"{type(exc).__name__}: {exc}"}

    if "mega" in requested:
        try:
            facts = MegaCollector().collect(show_date)
            normalized = [normalize_schedule_only(provider="mega", exhibitor_id="mega", run_id=run_id, cinema_id=f["cinemaId"], source_cinema_id=f.get("sourceCinemaId"), source_cinema_name=f.get("sourceCinemaName"), show_date=f["showDate"], collected_at=collected_at, session=f["session"], collector_version=MEGA_VERSION, source_url=f.get("scheduleUrl"), raw_payload_hash=f.get("schedulePayloadHash"), acquisition_warnings=f.get("errors") or []) for f in facts]
            snapshots.extend(normalized)
            statuses["mega"] = {"status": "ok-schedule-only", "snapshots": len(normalized), "seatMeasured": 0}
        except Exception as exc:
            statuses["mega"] = {"status": "error", "snapshots": 0, "error": f"{type(exc).__name__}: {exc}"}

    run_payload = {
        "schemaVersion": "1.0.0",
        "runId": run_id,
        "showDate": show_date,
        "collectedAt": collected_at,
        "policy": "read-only public observation; no seat selection, booking hold, order or payment action",
        "sourceStatuses": statuses,
        "snapshots": snapshots,
    }
    history_path = ROOT / "data/history" / show_date / f"{run_id}.json"
    run_path = ROOT / "data/runs" / f"{run_id}.json"
    write_json(history_path, run_payload)
    write_json(run_path, {k: v for k, v in run_payload.items() if k != "snapshots"} | {"snapshotCount": len(snapshots)})

    # Build browser products from all accumulated history, even if one source failed.
    from scripts.analytics.build_products import build_all_products
    build_all_products(ROOT)

    print(json.dumps({"runId": run_id, "showDate": show_date, "snapshots": len(snapshots), "sources": statuses}, indent=2))
    if not snapshots and not args.allow_empty:
        return 2
    if all(statuses.get(source, {}).get("status") == "error" for source in requested):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
