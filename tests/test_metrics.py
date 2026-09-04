import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.analytics.metrics import aggregate, cinema_rankings, seat_state_velocity


def load(name):
    return json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))


class MetricTests(unittest.TestCase):
    def test_unknown_seat_data_does_not_become_zero(self):
        gsc = load("session-snapshot.gsc.json")
        paragon = load("session-snapshot.schedule-only.json")
        summary = aggregate([gsc, paragon])
        self.assertEqual(summary["totalShows"], 2)
        self.assertEqual(summary["seatMeasuredSessions"], 1)
        self.assertEqual(summary["observedCapacity"], 246)
        self.assertEqual(summary["observedUsed"], 2)
        self.assertAlmostEqual(summary["seatCoverage"], 0.5)

    def test_weighted_occupancy(self):
        a = load("session-snapshot.gsc.json")
        b = deepcopy(a)
        b["cinemaId"] = "gsc-aman-central"
        b["sessionId"] = "b"
        b["seat"] = {"capacity": 100, "used": 50, "available": 50, "otherUnavailable": 0, "statusCounts": {"A": 50, "B": 50}}
        summary = aggregate([a, b])
        self.assertAlmostEqual(summary["occupancy"], 52 / 346)

    def test_performance_index(self):
        a = load("session-snapshot.gsc.json")
        a["seat"] = {"capacity": 100, "used": 20, "available": 80, "otherUnavailable": 0, "statusCounts": {"A": 80, "B": 20}}
        b = deepcopy(a)
        b["cinemaId"] = "gsc-aman-central"
        b["sessionId"] = "b"
        b["seat"] = {"capacity": 300, "used": 30, "available": 270, "otherUnavailable": 0, "statusCounts": {"A": 270, "B": 30}}
        rows = {r["cinemaId"]: r for r in cinema_rankings([a, b])}
        self.assertAlmostEqual(rows[a["cinemaId"]]["performanceIndex"], (20/50)/(100/400))
        self.assertAlmostEqual(rows[b["cinemaId"]]["performanceIndex"], (30/50)/(300/400))

    def test_aggregate_uses_latest_observation_per_session(self):
        earlier = load("session-snapshot.gsc.json")
        later = deepcopy(earlier)
        earlier["collectedAt"] = "2026-09-04T10:00:00+08:00"
        earlier["seat"]["used"] = 2
        later["collectedAt"] = "2026-09-04T11:00:00+08:00"
        later["seat"]["used"] = 8
        later["seat"]["available"] = 238
        summary = aggregate([later, earlier])
        self.assertEqual(summary["totalShows"], 1)
        self.assertEqual(summary["observedUsed"], 8)

    def test_velocity_can_be_negative(self):
        earlier = load("session-snapshot.tgv.json")
        later = deepcopy(earlier)
        earlier["collectedAt"] = "2026-09-04T10:00:00+08:00"
        earlier["seat"]["used"] = 10
        earlier["seat"]["available"] = 107
        later["collectedAt"] = "2026-09-04T12:00:00+08:00"
        later["seat"]["used"] = 6
        later["seat"]["available"] = 111
        result = seat_state_velocity(earlier, later)
        self.assertEqual(result["usedDelta"], -4)
        self.assertEqual(result["seatsPerHour"], -2)


if __name__ == "__main__":
    unittest.main()
