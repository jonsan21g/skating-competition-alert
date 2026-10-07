"""Competition monitor and state transition detection engine."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import DATA_DIR, STATE_FILE, load_watchlist
from .models import AlertEvent, AlertType, Competition
from .notifiers import get_active_notifiers
from .scraper import DsuCompetitionScraper

logger = logging.getLogger(__name__)


class CompetitionMonitor:
    """Tracks competition registration status and emits alerts on state changes."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = state_file or STATE_FILE
        self.scraper = DsuCompetitionScraper()
        self.watchlist_cfg = load_watchlist()

    def load_state(self) -> Dict[str, Competition]:
        """Loads previous snapshot from disk."""
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
                return {
                    k: Competition.from_dict(v)
                    for k, v in raw_data.items()
                }
        except Exception as e:
            logger.error(f"Error loading state from {self.state_file}: {e}")
            return {}

    def save_state(self, state: Dict[str, Competition]) -> None:
        """Saves current state snapshot to disk."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(
                    {k: v.to_dict() for k, v in state.items()},
                    f,
                    indent=2,
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.error(f"Error saving state to {self.state_file}: {e}")

    def match_watchlist(self, comp: Competition) -> Tuple[bool, Dict[str, Any]]:
        """
        Determines if a competition matches any watchlist rules.
        Returns (is_matched, rule_dict).
        """
        watched_list = self.watchlist_cfg.get("watched_competitions", [])
        title_lower = comp.title.lower()

        for item in watched_list:
            # Match by event_id if specified
            if "event_id" in item and str(item["event_id"]) == str(comp.event_id):
                return True, item

            # Match by keywords in title
            keywords = item.get("keywords", [])
            for kw in keywords:
                if kw.lower() in title_lower:
                    return True, item

            # Match by exact name
            name = item.get("name", "")
            if name and name.lower() in title_lower:
                return True, item

        return False, {}

    def detect_changes(
        self,
        current_comps: List[Competition],
        prev_state: Dict[str, Competition],
    ) -> List[AlertEvent]:
        """
        Compares freshly scraped competitions against previous state.
        Detects newly opened competitions, capacity changes, and reopened slots.
        """
        alerts: List[AlertEvent] = []
        global_settings = self.watchlist_cfg.get("global_settings", {})
        alert_on_any_new = global_settings.get("alert_on_any_new_open", True)
        low_spots_thresh = global_settings.get("warn_low_spots_threshold", 5)

        for curr in current_comps:
            matched, rules = self.match_watchlist(curr)
            prev = prev_state.get(curr.event_id)

            # Rule flags with sensible defaults
            alert_on_open = rules.get("alert_on_open", True) if matched else alert_on_any_new
            alert_on_sold_out = rules.get("alert_on_sold_out", True) if matched else False
            alert_on_reopened = rules.get("alert_on_reopened", True) if matched else True

            # ------------------------------------------------------------------
            # Scenario A: Brand new competition discovered
            # ------------------------------------------------------------------
            if prev is None:
                if curr.is_open and curr.spots_available > 0 and alert_on_open:
                    alerts.append(AlertEvent(
                        alert_type=AlertType.NEW_OPEN,
                        competition=curr,
                        message=f"New competition open for registration: {curr.title}",
                        new_spots_taken=curr.spots_taken,
                        new_status=curr.status,
                    ))
                elif curr.is_sold_out and not curr.is_closed and alert_on_sold_out:
                    alerts.append(AlertEvent(
                        alert_type=AlertType.SOLD_OUT,
                        competition=curr,
                        message=f"Discovered competition is currently sold out: {curr.title}",
                        new_spots_taken=curr.spots_taken,
                        new_status=curr.status,
                    ))
                continue

            # ------------------------------------------------------------------
            # Scenario B: Known competition state transitions
            # ------------------------------------------------------------------

            # 1. SPOT REOPENED! (Highest priority: was sold out, now has a spot open!)
            if prev.is_sold_out and not curr.is_sold_out and curr.spots_available > 0 and not curr.is_closed:
                if alert_on_reopened:
                    alerts.append(AlertEvent(
                        alert_type=AlertType.SPOT_REOPENED,
                        competition=curr,
                        message=f"A spot just reopened for {curr.title}! {curr.spots_available} spots available.",
                        old_spots_taken=prev.spots_taken,
                        new_spots_taken=curr.spots_taken,
                        old_status=prev.status,
                        new_status=curr.status,
                    ))

            # 2. Reached Sold Out
            elif not prev.is_sold_out and curr.is_sold_out and not curr.is_closed:
                if alert_on_sold_out:
                    alerts.append(AlertEvent(
                        alert_type=AlertType.SOLD_OUT,
                        competition=curr,
                        message=f"Competition {curr.title} reached capacity ({curr.spots_taken}/{curr.spots_max}).",
                        old_spots_taken=prev.spots_taken,
                        new_spots_taken=curr.spots_taken,
                        old_status=prev.status,
                        new_status=curr.status,
                    ))

            # 3. Registration Opened (status changed from closed/unopened to open)
            elif not prev.is_open and curr.is_open and curr.spots_available > 0:
                if alert_on_open:
                    alerts.append(AlertEvent(
                        alert_type=AlertType.REGISTRATION_OPENED,
                        competition=curr,
                        message=f"Registration has just opened for {curr.title}!",
                        old_status=prev.status,
                        new_status=curr.status,
                    ))

            # 4. Capacity Expanded (max spots increased)
            elif curr.spots_max > prev.spots_max and curr.spots_max > 0:
                alerts.append(AlertEvent(
                    alert_type=AlertType.CAPACITY_EXPANDED,
                    competition=curr,
                    message=f"Capacity expanded for {curr.title} from {prev.spots_max} to {curr.spots_max}!",
                    old_spots_taken=prev.spots_taken,
                    new_spots_taken=curr.spots_taken,
                ))

            # 5. Low spots remaining warning
            elif (
                curr.is_open
                and 0 < curr.spots_available <= low_spots_thresh
                and prev.spots_available > low_spots_thresh
            ):
                alerts.append(AlertEvent(
                    alert_type=AlertType.LOW_SPOTS,
                    competition=curr,
                    message=f"Hurry! Only {curr.spots_available} spots left for {curr.title}.",
                    old_spots_taken=prev.spots_taken,
                    new_spots_taken=curr.spots_taken,
                ))

        return alerts

    def run_check(self, dry_run: bool = False) -> List[AlertEvent]:
        """
        Executes a single check cycle:
        1. Loads previous state.
        2. Scrapes current competitions.
        3. Detects actionable changes.
        4. Dispatches notifications.
        5. Saves updated state (unless dry_run).
        """
        # Reload watchlist configuration in case user updated it
        self.watchlist_cfg = load_watchlist()

        prev_state = self.load_state()
        current_comps = self.scraper.fetch_competitions()

        alerts = self.detect_changes(current_comps, prev_state)

        if alerts:
            logger.info(f"Generated {len(alerts)} alert(s)!")
            notifiers = get_active_notifiers()
            for alert in alerts:
                subject = f"[DSU Alert] {alert.alert_type.value}: {alert.competition.title}"
                body = alert.format_notification()
                for n in notifiers:
                    try:
                        n.send(subject=subject, message=body)
                    except Exception as e:
                        logger.error(f"Notifier error: {e}")
        else:
            logger.info("No new registration status changes detected.")

        if not dry_run:
            new_state = {c.event_id: c for c in current_comps}
            self.save_state(new_state)

        return alerts
