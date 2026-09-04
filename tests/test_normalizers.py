import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.normalizers.gsc import normalize_gsc
from scripts.normalizers.tgv import normalize_tgv
from scripts.normalizers.schedule_only import normalize_schedule_only


class NormalizerTests(unittest.TestCase):
    def test_gsc_other_states_remain_separate(self):
        out = normalize_gsc(
            run_id="r", cinema_id="gsc-paradigm-jb", source_cinema_id="355",
            source_cinema_name="GSC Paradigm Mall (Johor Bahru)", show_date="2026-09-04",
            collected_at="2026-09-04T10:00:00+08:00", collector_version="test",
            session={"time":"13:00", "sessionId":"289353", "hall":"2", "type":"2D", "statusCounts":{"A":240,"B":2,"D":4}}
        )
        self.assertEqual(out["seat"]["capacity"], 246)
        self.assertEqual(out["seat"]["used"], 2)
        self.assertEqual(out["seat"]["otherUnavailable"], 4)

    def test_tgv_remaining_is_derived(self):
        out = normalize_tgv(
            run_id="r", cinema_id="tgv-1utama", source_cinema_id="BU0", source_cinema_name="1 UTAMA",
            show_date="2026-09-04", collected_at="2026-09-04T10:00:00+08:00", collector_version="test",
            session={"time":"15:00", "sessionId":"324726", "hall":"Cinema 1", "experience":"deluxe", "seatstotal":117, "seatsused":7}
        )
        self.assertEqual(out["seat"]["available"], 110)
        self.assertEqual(out["semantics"]["used"], "tgv-seatsused")

    def test_schedule_only_never_creates_seat_values(self):
        out = normalize_schedule_only(
            provider="paragon", exhibitor_id="paragon", run_id="r", cinema_id="paragon-ktcc",
            source_cinema_id="0000000004", source_cinema_name="Paragon Cinema KTCC",
            show_date="2026-09-04", collected_at="2026-09-04T10:00:00+08:00", collector_version="test",
            session={"time":"16:00", "sessionId":"83057", "hall":"Hall 3", "capacity":999}
        )
        self.assertIsNone(out["seat"]["capacity"])
        self.assertFalse(out["quality"]["seatMeasured"])


if __name__ == "__main__":
    unittest.main()

# Native source-session IDs must dominate generated identity so repeat observations
# of one screening remain comparable even if source metadata changes.
class SessionIdentityTests(unittest.TestCase):
    def test_native_session_id_precedes_time_fingerprint(self):
        from scripts.normalizers.common import session_identity
        a = session_identity("tgv-1utama", "2026-09-04", "15:00", "324678", "Cinema 3")
        b = session_identity("tgv-1utama", "2026-09-04", "15:05", "324678", "Cinema 3")
        self.assertEqual(a, b)
