"""Unit tests for sources configuration and competition matching."""

import unittest
from unittest.mock import patch, MagicMock
from src.config import load_sources, load_watchlist
from src.models import Competition, AlertType
from src.monitor import CompetitionMonitor
from src.scraper import DsuCompetitionScraper


class TestSourcesAndWatchlist(unittest.TestCase):

    def test_sources_json_structure(self):
        cfg = load_sources()
        self.assertIn("sources", cfg)
        sources = cfg["sources"]
        self.assertGreaterEqual(len(sources), 5)

        source_ids = [s["id"] for s in sources]
        self.assertIn("hiku_klubmodul", source_ids)
        self.assertIn("dsu_klubmodul", source_ids)
        self.assertIn("dsu_calendar", source_ids)
        self.assertIn("holdsport_flyver_cup", source_ids)
        self.assertIn("gsf_pingvin_cup", source_ids)

    def test_watchlist_contains_the_four_competitions(self):
        wl = load_watchlist()
        watched = wl.get("watched_competitions", [])
        names = [w["name"] for w in watched]
        self.assertIn("Forårskonkurrence Øst", names)
        self.assertIn("Isblomsten", names)
        self.assertIn("Pingvin Cup", names)
        self.assertIn("Flyver Cup", names)
        self.assertEqual(len(watched), 4)

        # Verify Isblomsten monitors hiku_klubmodul
        isblomsten = next(w for w in watched if w["name"] == "Isblomsten")
        self.assertIn("hiku_klubmodul", isblomsten.get("source_ids", []))

    def test_hiku_isblomsten_detection(self):
        """Test detecting Isblomsten registration when published on HIKU Klubmodul."""
        scraper = DsuCompetitionScraper()
        mock_api_data = {
            "Events": [
                {
                    "id": "850",
                    "name": "Isblomsten 2027",
                    "teaser": "Velkommen til Isblomsten 2027 i Herlev Skøjtehal",
                    "location": "Herlev Skating Arena",
                    "address": "Tvedvangen 204",
                    "start_date": "30.01.2027",
                    "end_date": "31.01.2027",
                    "enrollment_end": "05.01.2027",
                    "price": "550",
                    "sold_out": "false",
                    "waiting_list": "False",
                    "active": "1",
                }
            ]
        }

        with patch.object(scraper.session, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = mock_api_data
            mock_get.return_value = mock_resp

            comps = scraper._check_hiku_events()
            self.assertEqual(len(comps), 1)
            comp = comps[0]
            self.assertEqual(comp.event_id, "hiku_850")
            self.assertIn("Isblomsten", comp.title)
            self.assertTrue(comp.is_open)
            self.assertFalse(comp.is_sold_out)
            self.assertIn("EventID=850", comp.registration_url)
            self.assertEqual(comp.venue, "Herlev Skating Arena")

    def test_flyver_cup_spot_reopened_flow(self):
        monitor = CompetitionMonitor()
        prev = Competition(
            event_id="tsk_flyver_cup_2027",
            title="Flyver Cup 2027 (Tårnby Skøjteklub)",
            dates="12.02.2027-14.02.2027",
            deadline="15.11.2026 kl. 16:45",
            venue="Tårnby Skøjtehal",
            price="575 kr.",
            status="Udsolgt",
            spots_taken=200,
            spots_max=200,
            spots_available=0,
            is_open=False,
            is_sold_out=True,
            is_closed=False,
        )

        curr = Competition(
            event_id="tsk_flyver_cup_2027",
            title="Flyver Cup 2027 (Tårnby Skøjteklub)",
            dates="12.02.2027-14.02.2027",
            deadline="15.11.2026 kl. 16:45",
            venue="Tårnby Skøjtehal",
            price="575 kr.",
            status="Åben",
            spots_taken=199,
            spots_max=200,
            spots_available=1,
            is_open=True,
            is_sold_out=False,
            is_closed=False,
        )

        alerts = monitor.detect_changes([curr], {prev.event_id: prev})
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.SPOT_REOPENED)
        self.assertIn("Flyver Cup", alerts[0].competition.title)
        self.assertIn("1", str(alerts[0].competition.spots_available))

    def test_unrelated_competition_is_ignored(self):
        monitor = CompetitionMonitor()
        unrelated = Competition(
            event_id="999",
            title="Unrelated Training Camp 2026",
            dates="01.01.2026",
            deadline="01.01.2026",
            venue="Somewhere",
            price="100",
            status="Åben",
            spots_taken=5,
            spots_max=100,
            spots_available=95,
            is_open=True,
            is_sold_out=False,
            is_closed=False,
        )
        alerts = monitor.detect_changes([unrelated], {})
        self.assertEqual(len(alerts), 0)


if __name__ == "__main__":
    unittest.main()
