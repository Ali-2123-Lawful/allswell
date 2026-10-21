"""Data model for home-rhythm. Plain dataclasses, no third-party deps."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

# Event types we understand: the common vocabulary of home sensors and smart
# doorbells (motion / person / doorbell / delivery).
EVENT_TYPES = ("motion", "person", "doorbell", "delivery")


@dataclass(frozen=True)
class Event:
    """A single normalized sensor event.

    Attributes:
        id:        stable unique id
        type:      one of EVENT_TYPES
        zone:      logical area, e.g. "kitchen", "front_door", "bedroom"
        at:        timezone-aware (or naive-local) datetime the event occurred
        subtype:   optional refinement, e.g. "human", "package"
        device_id: optional source device id
    """

    id: str
    type: str
    zone: str
    at: datetime
    subtype: Optional[str] = None
    device_id: Optional[str] = None

    @property
    def minutes_into_day(self) -> int:
        """Minutes since local midnight: the unit every rhythm rule compares in."""
        return self.at.hour * 60 + self.at.minute


@dataclass
class ZoneProfile:
    """Learned normal behaviour for one zone."""

    zone: str
    # earliest minute-of-day this zone normally sees activity (e.g. kitchen ~ 7am)
    typical_first_minute: Optional[int] = None
    # latest minute-of-day this zone normally sees activity
    typical_last_minute: Optional[int] = None
    # average number of events per day in this zone
    avg_events_per_day: float = 0.0
    # how many of the baseline days had ANY activity in this zone
    days_seen: int = 0


@dataclass
class Baseline:
    """What a normal day looks like, learned from history."""

    zones: dict = field(default_factory=dict)  # zone -> ZoneProfile
    days_observed: int = 0
    # quiet window = hours when the home is normally still (for off-hours checks)
    quiet_start_minute: int = 0 * 60  # 00:00
    quiet_end_minute: int = 5 * 60 + 30  # 05:30
    # a zone whose activity normally starts by this minute is a "morning" zone;
    # if it has no activity by the grace cutoff today, that's a missing-routine flag
    morning_expected_by_minute: int = 10 * 60  # 10:00


@dataclass(frozen=True)
class Anomaly:
    """Something that broke the normal pattern."""

    code: str  # machine code, e.g. "OFF_HOURS_ACTIVITY"
    severity: str  # "info" | "warn" | "critical"
    title: str  # short human label
    detail: str  # one-line explanation grounded in the actual event
    zone: Optional[str] = None
    at: Optional[datetime] = None


@dataclass
class DayResult:
    """The verdict for a single day."""

    is_all_well: bool
    anomalies: List[Anomaly]
    events_considered: int
    zones_active: List[str]

    @property
    def headline_severity(self) -> str:
        """The most severe anomaly level today, or "ok" when all is well."""
        order = {"info": 0, "warn": 1, "critical": 2}
        if not self.anomalies:
            return "ok"
        return max((a.severity for a in self.anomalies), key=lambda s: order.get(s, 0))
