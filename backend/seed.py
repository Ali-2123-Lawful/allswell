"""
Deterministic demo timeline.

Builds a believable week of "normal" history plus a configurable "today", so the
demo is identical every run. Scenarios let the dashboard (or the demo operator)
switch between a calm day and each anomaly with one click — never relying on luck
during a live recording.

All events are emitted as plain dicts, loaded into backend/events.py:
    {id, type, zone, at (ISO), subtype, device_id}
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import List

ZONES_DEVICE = {
    "kitchen": "dev_kitchen_01",
    "front_door": "dev_frontdoor_01",
    "living_room": "dev_living_01",
    "bedroom": "dev_living_01",
}


def _ev(n: int, typ: str, zone: str, at: datetime, subtype: str | None = None) -> dict:
    return {
        "id": f"ev_{n}",
        "type": typ,
        "zone": zone,
        "at": at.isoformat(),
        "subtype": subtype,
        "device_id": ZONES_DEVICE.get(zone, "dev_frontdoor_01"),
    }


def _normal_day(day: datetime, n0: int) -> List[dict]:
    """A typical day for someone living alone: morning in the kitchen, a midday
    door, evening in the living room, settled by night."""
    n = n0
    out = []

    def add(typ: str, zone: str, h: int, m: int, sub: str | None = None) -> None:
        nonlocal n
        out.append(_ev(n, typ, zone, day.replace(hour=h, minute=m, second=0, microsecond=0), sub))
        n += 1

    add("motion", "kitchen", 7, 10)  # wakes, makes tea
    add("motion", "kitchen", 7, 35)
    add("motion", "living_room", 9, 5)
    add("person", "front_door", 11, 20, "human")  # steps out / mail
    add("motion", "kitchen", 12, 40)  # lunch
    add("motion", "living_room", 15, 0)
    add("motion", "living_room", 18, 30)  # evening
    add("motion", "kitchen", 19, 15)  # dinner
    add("motion", "living_room", 20, 45)
    return out


def history_events(days: int = 7, end_day: datetime | None = None) -> List[dict]:
    """`days` normal days ending the day before `end_day`."""
    end = end_day or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    out: List[dict] = []
    n = 0
    for d in range(days, 0, -1):
        day = end - timedelta(days=d)
        evs = _normal_day(day, n)
        out.extend(evs)
        n += len(evs)
    return out


def today_events(scenario: str, today: datetime | None = None) -> List[dict]:
    """Return today's events for a given scenario.

    Scenarios:
      normal            - a calm, on-rhythm day so far
      night_door        - someone at the front door at 3am (critical)
      missing_morning   - no kitchen activity by late morning (critical)
      unretrieved       - a delivery that nobody picked up (warn)
      restless_night    - repeated night movement (warn)
    """
    base = (today or datetime.now()).replace(second=0, microsecond=0)
    day = base.replace(hour=0, minute=0)
    n = 900  # high offset so ids don't clash with history
    out: List[dict] = []

    def add(typ: str, zone: str, h: int, m: int, sub: str | None = None) -> None:
        nonlocal n
        out.append(_ev(n, typ, zone, day.replace(hour=h, minute=m), sub))
        n += 1

    # a normal morning has already happened in every scenario except missing_morning
    if scenario != "missing_morning":
        add("motion", "kitchen", 7, 20)
        add("motion", "kitchen", 7, 50)
        add("motion", "living_room", 9, 30)

    if scenario == "normal":
        add("person", "front_door", 11, 15, "human")
        add("motion", "kitchen", 12, 35)

    elif scenario == "night_door":
        # the headline anomaly: front-door doorbell in the dead of night
        add("doorbell", "front_door", 3, 4, "human")
        add("motion", "front_door", 3, 5)
        add("motion", "kitchen", 12, 35)

    elif scenario == "missing_morning":
        # nothing in the kitchen at all today; only a little living-room motion
        add("motion", "living_room", 9, 10)

    elif scenario == "unretrieved":
        add("delivery", "front_door", 9, 45, "package")
        add("motion", "kitchen", 12, 35)
        # note: no front_door person event after the delivery -> unretrieved

    elif scenario == "restless_night":
        add("motion", "bedroom", 1, 10)
        add("motion", "living_room", 2, 30)
        add("motion", "kitchen", 3, 50)
        add("motion", "living_room", 4, 20)

    return out


SCENARIOS = {
    "normal": "A calm day, on rhythm",
    "night_door": "Front door at 3 AM (critical)",
    "missing_morning": "No morning routine (critical)",
    "unretrieved": "Delivery not picked up (warn)",
    "restless_night": "Restless night (warn)",
}
