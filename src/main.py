"""Main CLI entrypoint for skating-competition-alert."""

import argparse
import logging
import sys
import time
from datetime import datetime
from typing import List

from .config import AppConfig, load_watchlist, save_watchlist
from .models import AlertEvent, AlertType, Competition
from .monitor import CompetitionMonitor
from .notifiers import get_active_notifiers
from .scraper import DsuCompetitionScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("skating-alert")

# Ensure UTF-8 output across Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_status_table(competitions: List[Competition]) -> None:
    """Renders a clean, informative terminal status table of competitions."""
    sep = "=" * 105
    header = f"{'ID':<6} | {'COMPETITION':<35} | {'STATUS':<9} | {'SPOTS':<9} | {'DEADLINE':<11} | {'VENUE':<25}"
    print("\n" + sep)
    print("               DANISH FIGURE SKATING (DSU) COMPETITION REGISTRATION STATUS")
    print(sep)
    print(header)
    print("-" * 105)

    for c in competitions:
        # Determine spots string
        spots = f"{c.spots_taken}/{c.spots_max}" if c.spots_max else f"{c.spots_taken}"
        
        # Color or tag status
        status_disp = c.status
        if c.is_sold_out and not c.is_closed:
            status_disp = "SOLD OUT"
        elif c.is_open:
            status_disp = "OPEN"
        elif c.is_closed:
            status_disp = "CLOSED"

        title_short = (c.title[:32] + "...") if len(c.title) > 35 else c.title
        venue_short = (c.venue[:22] + "...") if len(c.venue) > 25 else (c.venue or "-")

        print(
            f"{c.event_id:<6} | {title_short:<35} | {status_disp:<9} | {spots:<9} | {c.deadline:<11} | {venue_short:<25}"
        )

    print(sep + "\n")


def cmd_watch(name: str) -> None:
    """Adds a new competition keyword to watchlist.json."""
    data = load_watchlist()
    watched = data.get("watched_competitions", [])

    # Check if already in list
    for w in watched:
        if w.get("name", "").lower() == name.lower():
            print(f"Competition '{name}' is already being monitored.")
            return

    new_entry = {
        "name": name,
        "keywords": [name],
        "alert_on_open": True,
        "alert_on_sold_out": True,
        "alert_on_reopened": True,
        "alert_deadline_hours": [48, 24],
    }
    watched.append(new_entry)
    data["watched_competitions"] = watched
    save_watchlist(data)
    print(f"Successfully added '{name}' to watched competitions list in config/watchlist.json!")


def cmd_unwatch(name: str) -> None:
    """Removes a competition from watchlist.json."""
    data = load_watchlist()
    watched = data.get("watched_competitions", [])
    filtered = [w for w in watched if w.get("name", "").lower() != name.lower()]

    if len(filtered) == len(watched):
        print(f"No entry found matching '{name}'.")
    else:
        data["watched_competitions"] = filtered
        save_watchlist(data)
        print(f"Successfully removed '{name}' from watchlist.")


def cmd_test_alert() -> None:
    """Sends a sample test alert across all configured notifiers."""
    sample_comp = Competition(
        event_id="999",
        title="Test Skøjte Cup 2026",
        dates="15.12.2026-17.12.2026",
        deadline="01.12.2026",
        venue="Skøjteklub København",
        price="535 kr.",
        status="Åben",
        spots_taken=199,
        spots_max=200,
        spots_available=1,
        is_open=True,
        is_sold_out=False,
        is_closed=False,
        registration_url="https://dsu.klub-modul.dk/cms/EventOverviewList.aspx",
    )
    alert = AlertEvent(
        alert_type=AlertType.SPOT_REOPENED,
        competition=sample_comp,
        message="A spot just reopened for Test Skøjte Cup 2026! 1 spot available.",
        old_spots_taken=200,
        new_spots_taken=199,
    )

    notifiers = get_active_notifiers()
    print(f"Testing alert dispatch across {len(notifiers)} active notifier(s)...")
    for n in notifiers:
        success = n.send(
            subject=f"[TEST] {alert.alert_type.value}: {sample_comp.title}",
            message=alert.format_notification(),
        )
        print(f"Notifier {n.__class__.__name__}: {'SUCCESS' if success else 'FAILED'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dansk Skøjte Union (DSU) Skating Competition Registration Alert Engine"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run a single scrape and check for registration status changes",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display current live registration status table of all DSU competitions",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run continuously in background polling mode",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=AppConfig.CHECK_INTERVAL_SECONDS,
        help=f"Polling interval in seconds for daemon mode (default: {AppConfig.CHECK_INTERVAL_SECONDS}s)",
    )
    parser.add_argument(
        "--watch",
        type=str,
        help="Add a competition name/keyword to config/watchlist.json",
    )
    parser.add_argument(
        "--unwatch",
        type=str,
        help="Remove a competition from config/watchlist.json",
    )
    parser.add_argument(
        "--test-alert",
        action="store_true",
        help="Send a test notification to verify active dispatchers",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform check without persisting state or triggering live notification alerts",
    )

    args = parser.parse_args()

    if args.watch:
        cmd_watch(args.watch)
        return

    if args.unwatch:
        cmd_unwatch(args.unwatch)
        return

    if args.test_alert:
        cmd_test_alert()
        return

    if args.status:
        scraper = DsuCompetitionScraper()
        competitions = scraper.fetch_competitions()
        print_status_table(competitions)
        return

    monitor = CompetitionMonitor()

    if args.daemon:
        logger.info(
            f"Starting Skating Competition Alert daemon (Polling every {args.interval}s)..."
        )
        try:
            while True:
                logger.info(f"Checking DSU competitions at {datetime.now().strftime('%H:%M:%S')}...")
                monitor.run_check(dry_run=args.dry_run)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user.")
        return

    # Default action: single check
    logger.info("Executing single DSU competition check...")
    alerts = monitor.run_check(dry_run=args.dry_run)
    if alerts:
        print(f"\nDispatched {len(alerts)} notification alert(s)!")
    else:
        print("\nAll clear! No new openings or spot changes detected.")


if __name__ == "__main__":
    main()
