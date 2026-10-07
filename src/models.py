"""Data models for skating-competition-alert."""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime


class AlertType(str, Enum):
    """Types of competition alerts."""
    NEW_OPEN = "NEW_OPEN"                    # Brand new competition discovered with open registration
    REGISTRATION_OPENED = "REGISTRATION_OPENED"  # Known competition changed status to open
    SOLD_OUT = "SOLD_OUT"                    # Hit capacity (spots full) but not closed
    SPOT_REOPENED = "SPOT_REOPENED"          # Previously sold-out competition now has an open spot!
    CAPACITY_EXPANDED = "CAPACITY_EXPANDED"  # Total quota increased (e.g. 200 -> 250)
    LOW_SPOTS = "LOW_SPOTS"                  # Spots running out fast (below threshold)
    DEADLINE_WARNING = "DEADLINE_WARNING"    # Registration deadline approaching


@dataclass
class Competition:
    """Represents a Danish figure skating competition listed on DSU Klubmodul."""
    event_id: str
    title: str
    dates: str
    deadline: str
    venue: str
    price: str
    status: str                         # e.g. "Åben", "Lukket", "Udsolgt"
    spots_taken: int
    spots_max: int
    spots_available: int
    is_open: bool
    is_sold_out: bool
    is_closed: bool
    categories: List[str] = field(default_factory=list)
    registration_url: str = ""
    participants_url: str = ""
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Competition":
        """Instantiate from dictionary."""
        return cls(
            event_id=str(data.get("event_id", "")),
            title=data.get("title", ""),
            dates=data.get("dates", ""),
            deadline=data.get("deadline", ""),
            venue=data.get("venue", ""),
            price=data.get("price", ""),
            status=data.get("status", ""),
            spots_taken=int(data.get("spots_taken", 0)),
            spots_max=int(data.get("spots_max", 0)),
            spots_available=int(data.get("spots_available", 0)),
            is_open=bool(data.get("is_open", False)),
            is_sold_out=bool(data.get("is_sold_out", False)),
            is_closed=bool(data.get("is_closed", False)),
            categories=data.get("categories", []),
            registration_url=data.get("registration_url", ""),
            participants_url=data.get("participants_url", ""),
            last_seen=data.get("last_seen", datetime.now().isoformat()),
        )


@dataclass
class AlertEvent:
    """Represents an actionable alert event to be dispatched."""
    alert_type: AlertType
    competition: Competition
    message: str
    old_spots_taken: Optional[int] = None
    new_spots_taken: Optional[int] = None
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def format_notification(self) -> str:
        """Creates a high-urgency, user-friendly notification message."""
        comp = self.competition
        url = comp.registration_url or "https://dsu.klub-modul.dk/cms/EventOverviewList.aspx"

        if self.alert_type == AlertType.SPOT_REOPENED:
            header = "🚨 [DSU SKATING ALERT] SPOT REOPENED!"
            body = (
                f"{header}\n\n"
                f"🏆 {comp.title}\n"
                f"🎟️ Spots Available: {comp.spots_available} / {comp.spots_max} (Was sold out!)\n"
                f"📍 Venue: {comp.venue or 'TBA'}\n"
                f"📅 Dates: {comp.dates}\n"
                f"⏰ Deadline: {comp.deadline}\n\n"
                f"⚡ Act quickly! Slots fill within minutes.\n"
                f"👉 Register NOW: {url}"
            )
        elif self.alert_type in (AlertType.NEW_OPEN, AlertType.REGISTRATION_OPENED):
            header = "⛸️ [DSU SKATING ALERT] REGISTRATION OPEN!"
            body = (
                f"{header}\n\n"
                f"🏆 {comp.title}\n"
                f"🎟️ Available Spots: {comp.spots_available} / {comp.spots_max}\n"
                f"📍 Venue: {comp.venue or 'TBA'}\n"
                f"📅 Dates: {comp.dates}\n"
                f"⏰ Deadline: {comp.deadline}\n"
                f"💰 Price: {comp.price}\n\n"
                f"👉 Register here: {url}"
            )
        elif self.alert_type == AlertType.SOLD_OUT:
            header = "⚠️ [DSU SKATING NOTICE] COMPETITION SOLD OUT"
            body = (
                f"{header}\n\n"
                f"🏆 {comp.title}\n"
                f"🎟️ Capacity reached: {comp.spots_taken} / {comp.spots_max}\n"
                f"⏰ Registration deadline is {comp.deadline}.\n\n"
                f"👀 System is actively monitoring this competition. You will receive an immediate alert if any skater withdraws and a spot reopens!"
            )
        elif self.alert_type == AlertType.CAPACITY_EXPANDED:
            header = "📈 [DSU SKATING ALERT] CAPACITY EXPANDED!"
            body = (
                f"{header}\n\n"
                f"🏆 {comp.title}\n"
                f"🎟️ Quota expanded to {comp.spots_max}! Currently {comp.spots_taken}/{comp.spots_max} taken.\n"
                f"🎟️ Open spots: {comp.spots_available}\n\n"
                f"👉 Register here: {url}"
            )
        elif self.alert_type == AlertType.LOW_SPOTS:
            header = "⚡ [DSU SKATING WARNING] ONLY A FEW SPOTS LEFT!"
            body = (
                f"{header}\n\n"
                f"🏆 {comp.title}\n"
                f"⚠️ Only {comp.spots_available} spots left! ({comp.spots_taken} / {comp.spots_max})\n"
                f"⏰ Deadline: {comp.deadline}\n\n"
                f"👉 Secure your spot now: {url}"
            )
        else:
            header = f"ℹ️ [DSU SKATING UPDATE] {self.alert_type.value}"
            body = (
                f"{header}\n\n"
                f"🏆 {comp.title}\n"
                f"Status: {comp.status}\n"
                f"Spots: {comp.spots_taken}/{comp.spots_max}\n"
                f"👉 {url}"
            )

        return body
