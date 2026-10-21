"""
Home-activity event store
=========================

An in-memory stream of home-sensor events (motion, person, doorbell, delivery).
The scenario simulator (seed.py) fills it; backend/care.py reads it. In a real
deployment this would be fed by the home's sensors instead.
"""

from __future__ import annotations

from datetime import datetime
from typing import List

from packages.home_rhythm import Event

_EVENTS: List[Event] = []


def load(raw_events: List[dict]) -> None:
    """Replace the whole stream with a timeline of raw event dicts."""
    _EVENTS[:] = [
        Event(
            id=ev["id"],
            type=ev["type"],
            zone=ev["zone"],
            at=datetime.fromisoformat(ev["at"]),
            subtype=ev.get("subtype"),
            device_id=ev.get("device_id"),
        )
        for ev in raw_events
    ]


def all_events() -> List[Event]:
    return list(_EVENTS)
