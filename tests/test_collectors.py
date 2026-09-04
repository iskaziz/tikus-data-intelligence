import json
import unittest
from pathlib import Path

from scripts.collectors.gsc import parse_showtimes_xml, parse_seat_status_xml
from scripts.collectors.tgv import extract_sessions, extract_seat_status

FIX = Path(__file__).parent / "fixtures"


class CollectorParserTests(unittest.TestCase):
    def test_gsc_showtime_parser_keeps_native_identifiers(self):
        xml = (FIX / "gsc_showtimes.xml").read_text()
        tracked = {"210": {"id": "gsc-mid-valley", "name": "GSC Mid Valley Megamall"}}
        rows = parse_showtimes_xml(xml, tracked)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sessionId"], "924428")
        self.assertEqual(rows[0]["hallId"], "2")
        self.assertEqual(rows[0]["time"], "20:00")
        self.assertEqual(rows[0]["cinemaId"], "gsc-mid-valley")

    def test_gsc_seat_parser_preserves_other_state(self):
        data = parse_seat_status_xml((FIX / "gsc_seats.xml").read_text())
        self.assertEqual(data["statusCounts"], {"A": 2, "B": 1, "D": 1})
        self.assertEqual(data["seatTypeCounts"], {"N": 3, "H": 1})

    def test_tgv_schedule_parser(self):
        payload = json.loads((FIX / "tgv_schedule.json").read_text())
        name, sessions = extract_sessions(payload, "BBT")
        self.assertEqual(name, "BUKIT TINGGI")
        self.assertEqual(sessions[0]["sessionId"], "409356")
        self.assertEqual(sessions[0]["time"], "14:10")
        self.assertEqual(sessions[0]["hall"], "Cinema 3")
        self.assertEqual(sessions[0]["format"], "2D")

    def test_tgv_seat_parser(self):
        payload = json.loads((FIX / "tgv_seatstatus.json").read_text())
        seats = extract_seat_status(payload)
        self.assertEqual(seats["409356"]["seatstotal"], 115)
        self.assertEqual(seats["409356"]["seatsused"], 1)


if __name__ == "__main__":
    unittest.main()
