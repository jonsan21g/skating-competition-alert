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


def print_status_table(competitions: List[Competition], show_all: bool = False) -> None:
    """Renders a clean, informative terminal status table of competitions."""
    monitor = CompetitionMonitor()
    
    # Partition into watched vs other
    watched_comps = []
    other_comps = []
    for c in competitions:
        is_watched, _ = monitor.match_watchlist(c)
        if is_watched:
            watched_comps.append(c)
        else:
            other_comps.append(c)

    display_list = watched_comps if not show_all else (watched_comps + other_comps)

    sep = "=" * 115
    header = f"{'ID':<30} | {'COMPETITION':<35} | {'STATUS':<9} | {'SPOTS':<9} | {'DEADLINE':<18} | {'VENUE':<20}"
    print("\n" + sep)
    print("                     TRACKED FIGURE SKATING COMPETITION REGISTRATION STATUS")
    print(sep)
    print(header)
    print("-" * 115)

    for c in display_list:
        spots = f"{c.spots_taken}/{c.spots_max}" if c.spots_max else f"{c.spots_taken}"
        
        status_disp = c.status
        if c.is_sold_out and not c.is_closed:
            status_disp = "SOLD OUT"
        elif c.is_open:
            status_disp = "OPEN"
        elif c.is_closed:
            status_disp = "CLOSED"

        title_short = (c.title[:32] + "...") if len(c.title) > 35 else c.title
        venue_short = (c.venue[:17] + "...") if len(c.venue) > 20 else (c.venue or "-")
        id_short = (c.event_id[:27] + "...") if len(c.event_id) > 30 else c.event_id
        deadline_short = (c.deadline[:16] + "...") if len(c.deadline) > 18 else c.deadline

        print(
            f"{id_short:<30} | {title_short:<35} | {status_disp:<9} | {spots:<9} | {deadline_short:<18} | {venue_short:<20}"
        )

    print(sep)
    if not show_all and other_comps:
        print(f"Showing {len(watched_comps)} tracked competitions. Use --all to view {len(other_comps)} other DSU events.\n")
    else:
        print()


def cmd_watch(name: str) -> None:
    """Adds a new competition keyword to watchlist.json."""
    data = load_watchlist()
    watched = data.get("watched_competitions", [])

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
    """Sends a sample test alert across configured notifiers (WhatsApp / Console)."""
    sample_comp = Competition(
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
        registration_url="https://www.holdsport.dk/public_ticket_events/flyver-cup-20276",
    )
    alert = AlertEvent(
        alert_type=AlertType.SPOT_REOPENED,
        competition=sample_comp,
        message="A spot just reopened for Flyver Cup 2027! 1 spot available.",
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
        description="Figure Skating Competition Registration Alert Engine (WhatsApp & DSU)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run a single scrape and check for registration status changes",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Display current live registration status table of tracked competitions",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="When used with --status, displays all scraped DSU competitions",
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
        print_status_table(competitions, show_all=args.all)
        return

    monitor = CompetitionMonitor()

    if args.daemon:
        logger.info(
            f"Starting Skating Competition Alert daemon (Polling every {args.interval}s)..."
        )
        try:
            while True:
                logger.info(f"Checking competitions at {datetime.now().strftime('%H:%M:%S')}...")
                monitor.run_check(dry_run=args.dry_run)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Daemon stopped by user.")
        return

    # Default action: single check
    logger.info("Executing single competition check...")
    alerts = monitor.run_check(dry_run=args.dry_run)
    if alerts:
        print(f"\nDispatched {len(alerts)} notification alert(s)!")
    else:
        print("\nAll clear! No new openings or spot changes detected for tracked competitions.")


if __name__ == "__main__":
    main()
