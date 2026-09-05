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

class ScheduleOnlyCollectorParserTests(unittest.TestCase):
    def test_paragon_tikus_times(self):
        from scripts.collectors.paragon import parse_tikus_times
        html = (FIX / "paragon_tikus.html").read_text(encoding="utf-8")
        self.assertEqual(parse_tikus_times(html, "2026-09-04"), ["04:30 PM", "06:30 PM", "08:30 PM"])

    def test_paragon_does_not_leak_stray_midnight_time(self):
        from scripts.collectors.paragon import parse_tikus_times
        html = (FIX / "paragon_tikus.html").read_text(encoding="utf-8")
        times = parse_tikus_times(html, "2026-09-04")
        self.assertNotIn("12:30 AM", times)
        self.assertNotIn("11:55 PM", times)

    def test_paragon_future_date_is_scoped_to_tikus_card(self):
        from scripts.collectors.paragon import parse_tikus_times
        html = (FIX / "paragon_tikus.html").read_text(encoding="utf-8")
        self.assertEqual(parse_tikus_times(html, "2026-09-05"), ["10:30 AM", "04:30 PM"])


    def test_paragon_uses_movie_and_ticket_anchor_semantics(self):
        from scripts.collectors.paragon import parse_tikus_schedule
        html = (FIX / "paragon_tikus.html").read_text(encoding="utf-8")
        rows, diagnostics = parse_tikus_schedule(html, "2026-09-04")
        self.assertEqual([r["sessionId"] for r in rows], ["163017", "183017", "203017"])
        self.assertEqual(diagnostics["tikusTitleAnchors"], 1)
        self.assertEqual(diagnostics["matchedDateTicketAnchors"], 3)

    def test_paragon_ignores_plain_text_tikus_without_movie_href(self):
        from scripts.collectors.paragon import parse_tikus_schedule
        html = '<span>Tikus!</span><h4>Saturday, 05 September 2026</h4><a href="/Ticketing/visSelectTickets.aspx?txtSessionId=003000">12:30 AM</a>'
        rows, diagnostics = parse_tikus_schedule(html, "2026-09-05")
        self.assertEqual(rows, [])
        self.assertEqual(diagnostics["rejectionReasons"].get("no-exact-tikus-movie-anchor"), 1)

    def test_mega_riverfront_times(self):
        from scripts.collectors.mega import parse_riverfront_times
        html = (FIX / "mega_tikus.html").read_text(encoding="utf-8")
        self.assertEqual(parse_riverfront_times(html, "2026-09-05"), ["12:50 PM", "01:30 PM", "07:05 PM", "10:40 PM"])
