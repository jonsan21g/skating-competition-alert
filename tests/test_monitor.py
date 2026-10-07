"""Unit tests for competition monitor and state change detection."""

import unittest
from pathlib import Path
import tempfile
from src.monitor import CompetitionMonitor
from src.models import Competition, AlertType


class TestCompetitionMonitor(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "test_state.json"
        self.monitor = CompetitionMonitor(state_file=self.state_file)
        # Mock watchlist configuration
        self.monitor.watchlist_cfg = {
            "global_settings": {
                "alert_on_any_new_open": True,
                "warn_low_spots_threshold": 5,
            },
            "watched_competitions": [
                {
                    "name": "Sjællands Cup",
                    "keywords": ["Sjællands Cup", "Sjaellands Cup"],
                    "alert_on_open": True,
                    "alert_on_sold_out": True,
                    "alert_on_reopened": True,
                },
                {
                    "name": "Isblomsten",
                    "keywords": ["Isblomsten"],
                    "alert_on_open": True,
                    "alert_on_sold_out": True,
                    "alert_on_reopened": True,
                }
            ],
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_spot_reopened_detection(self):
        """CRITICAL: Test that when a sold-out competition frees a slot, an alert is immediately raised."""
        prev_comp = Competition(
            event_id="69",
            title="Sjællands Cup 2026",
            dates="13.11.2026-15.11.2026",
            deadline="08.10.2026",
            venue="Skøjteklub København",
            price="535 kr.",
            status="Venteliste",
            spots_taken=200,
            spots_max=200,
            spots_available=0,
            is_open=False,
            is_sold_out=True,
            is_closed=False,
        )
        prev_state = {"69": prev_comp}

        # A skater withdrew! Now 199/200, status back to Åben
        curr_comp = Competition(
            event_id="69",
            title="Sjællands Cup 2026",
            dates="13.11.2026-15.11.2026",
            deadline="08.10.2026",
            venue="Skøjteklub København",
            price="535 kr.",
            status="Åben",
            spots_taken=199,
            spots_max=200,
            spots_available=1,
            is_open=True,
            is_sold_out=False,
            is_closed=False,
        )

        alerts = self.monitor.detect_changes([curr_comp], prev_state)
        self.assertEqual(len(alerts), 1)
        alert = alerts[0]
        self.assertEqual(alert.alert_type, AlertType.SPOT_REOPENED)
        self.assertEqual(alert.old_spots_taken, 200)
        self.assertEqual(alert.new_spots_taken, 199)
        self.assertIn("SPOT REOPENED", alert.format_notification())
        self.assertIn("1 / 200", alert.format_notification())

    def test_sold_out_detection(self):
        """Test alerting when a watched competition hits full capacity."""
        prev_comp = Competition(
            event_id="69",
            title="Sjællands Cup 2026",
            dates="13.11.2026-15.11.2026",
            deadline="08.10.2026",
            venue="Skøjteklub København",
            price="535 kr.",
            status="Åben",
            spots_taken=198,
            spots_max=200,
            spots_available=2,
            is_open=True,
            is_sold_out=False,
            is_closed=False,
        )
        prev_state = {"69": prev_comp}

        curr_comp = Competition(
            event_id="69",
            title="Sjællands Cup 2026",
            dates="13.11.2026-15.11.2026",
            deadline="08.10.2026",
            venue="Skøjteklub København",
            price="535 kr.",
            status="Udsolgt",
            spots_taken=200,
            spots_max=200,
            spots_available=0,
            is_open=False,
            is_sold_out=True,
            is_closed=False,
        )

        alerts = self.monitor.detect_changes([curr_comp], prev_state)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.SOLD_OUT)
        self.assertIn("SOLD OUT", alerts[0].format_notification())

    def test_new_open_competition_detection(self):
        """Test discovering a brand new competition that is open."""
        new_comp = Competition(
            event_id="105",
            title="Isblomsten 2026",
            dates="20.01.2026-22.01.2026",
            deadline="10.01.2026",
            venue="Herlev",
            price="500 kr.",
            status="Åben",
            spots_taken=15,
            spots_max=200,
            spots_available=185,
            is_open=True,
            is_sold_out=False,
            is_closed=False,
        )

        alerts = self.monitor.detect_changes([new_comp], {})
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].alert_type, AlertType.NEW_OPEN)
        self.assertIn("REGISTRATION OPEN", alerts[0].format_notification())

    def test_capacity_expansion_detection(self):
        """Test detecting when organizers raise the quota."""
        prev_comp = Competition(
            event_id="69",
            title="Sjællands Cup 2026",
            dates="13.11.2026-15.11.2026",
            deadline="08.10.2026",
            venue="Skøjteklub København",
            price="535 kr.",
            status="Udsolgt",
            spots_taken=200,
            spots_max=200,
            spots_available=0,
            is_open=False,
            is_sold_out=True,
            is_closed=False,
        )
        prev_state = {"69": prev_comp}

        # Organizers expanded to 250 spots
        curr_comp = Competition(
            event_id="69",
            title="Sjællands Cup 2026",
            dates="13.11.2026-15.11.2026",
            deadline="08.10.2026",
            venue="Skøjteklub København",
            price="535 kr.",
            status="Åben",
            spots_taken=200,
            spots_max=250,
            spots_available=50,
            is_open=True,
            is_sold_out=False,
            is_closed=False,
        )

        alerts = self.monitor.detect_changes([curr_comp], prev_state)
        self.assertTrue(any(a.alert_type in (AlertType.SPOT_REOPENED, AlertType.CAPACITY_EXPANDED) for a in alerts))


if __name__ == "__main__":
    unittest.main()
