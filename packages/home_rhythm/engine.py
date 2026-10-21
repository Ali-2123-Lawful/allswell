"""The rhythm engine: learn a baseline, then evaluate a day against it.

No ML, no dependencies — just rolling statistics and a handful of rules that
map directly onto how a caregiver actually thinks about a relative's day:

  * Did the morning routine happen?          -> MISSING_MORNING_ROUTINE
  * Was there activity in the dead of night? -> OFF_HOURS_ACTIVITY
  * Did a delivery just sit there?           -> UNRETRIEVED_DELIVERY
  * Lots of restless night movement?         -> REPEATED_NIGHT_ACTIVITY

Everything is explainable: each anomaly carries the real event time/zone so the
digest layer (or a human) can say exactly what happened.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional

from .model import Anomaly, Baseline, DayResult, Event, ZoneProfile


def _day_of(ev: Event) -> date:
    return ev.at.date()


def _fmt(at: datetime) -> str:
    # 3:04 AM style, no leading zero on the hour
    return at.strftime("%I:%M %p").lstrip("0") if hasattr(at, "strftime") else str(at)


def build_baseline(
    history: Iterable[Event],
    *,
    quiet_start_hour: int = 0,
    quiet_end_hour: float = 5.5,
    morning_expected_hour: int = 10,
) -> Baseline:
    """Learn a normal day from historical events (everything before today)."""

    events = list(history)
    by_day_zone: Dict[date, Dict[str, List[Event]]] = defaultdict(lambda: defaultdict(list))
    for ev in events:
        by_day_zone[_day_of(ev)][ev.zone].append(ev)

    days = sorted(by_day_zone.keys())
    baseline = Baseline(
        days_observed=len(days),
        quiet_start_minute=int(quiet_start_hour * 60),
        quiet_end_minute=int(quiet_end_hour * 60),
        morning_expected_by_minute=int(morning_expected_hour * 60),
    )

    # Aggregate per-zone statistics across days.
    firsts: Dict[str, List[int]] = defaultdict(list)
    lasts: Dict[str, List[int]] = defaultdict(list)
    counts: Dict[str, List[int]] = defaultdict(list)
    days_seen: Dict[str, int] = defaultdict(int)

    for d in days:
        for zone, evs in by_day_zone[d].items():
            evs_sorted = sorted(evs, key=lambda e: e.minutes_into_day)
            firsts[zone].append(evs_sorted[0].minutes_into_day)
            lasts[zone].append(evs_sorted[-1].minutes_into_day)
            counts[zone].append(len(evs))
            days_seen[zone] += 1

    for zone in counts:
        baseline.zones[zone] = ZoneProfile(
            zone=zone,
            typical_first_minute=_median(firsts[zone]),
            typical_last_minute=_median(lasts[zone]),
            avg_events_per_day=sum(counts[zone]) / len(counts[zone]),
            days_seen=days_seen[zone],
        )

    return baseline


def evaluate_day(
    today: Iterable[Event],
    baseline: Baseline,
    *,
    now: Optional[datetime] = None,
    delivery_grace_minutes: int = 90,
    night_activity_threshold: int = 3,
) -> DayResult:
    """Compare today's events to the baseline and surface anomalies."""

    events = sorted(today, key=lambda e: e.at)
    anomalies: List[Anomaly] = []
    zones_active = sorted({e.zone for e in events})

    ref_now = now or (events[-1].at if events else datetime.now())
    now_minute = ref_now.hour * 60 + ref_now.minute

    # --- Rule 1: missing morning routine ------------------------------------
    # For any zone the baseline considers a reliable "morning" zone (normally
    # active before the expected cutoff, seen on most days), flag if today has
    # no activity there yet and we're already past the grace cutoff.
    if now_minute >= baseline.morning_expected_by_minute:
        active_zones_today = {e.zone for e in events}
        for zone, prof in baseline.zones.items():
            reliable = prof.days_seen >= max(2, int(baseline.days_observed * 0.6))
            is_morning_zone = (
                prof.typical_first_minute is not None
                and prof.typical_first_minute <= baseline.morning_expected_by_minute
            )
            if reliable and is_morning_zone and zone not in active_zones_today:
                anomalies.append(
                    Anomaly(
                        code="MISSING_MORNING_ROUTINE",
                        severity="critical",
                        title="Morning routine hasn't started",
                        detail=(
                            f"No {zone.replace('_', ' ')} activity yet today. "
                            f"It normally begins around {_minute_label(prof.typical_first_minute)}."
                        ),
                        zone=zone,
                    )
                )

    # --- Rule 2: off-hours activity -----------------------------------------
    for ev in events:
        m = ev.minutes_into_day
        in_quiet = baseline.quiet_start_minute <= m < baseline.quiet_end_minute
        if in_quiet and ev.type in ("doorbell", "person", "motion"):
            sev = "critical" if ev.zone == "front_door" or ev.type in ("doorbell", "person") else "warn"
            anomalies.append(
                Anomaly(
                    code="OFF_HOURS_ACTIVITY",
                    severity=sev,
                    title="Activity during the quiet hours",
                    detail=(
                        f"{_event_phrase(ev)} at {_fmt(ev.at)} — the home is normally "
                        f"still between {_minute_label(baseline.quiet_start_minute)} "
                        f"and {_minute_label(baseline.quiet_end_minute)}."
                    ),
                    zone=ev.zone,
                    at=ev.at,
                )
            )

    # --- Rule 3: unretrieved delivery ---------------------------------------
    deliveries = [e for e in events if e.type == "delivery"]
    for d in deliveries:
        retrieved = any(
            e.zone == d.zone
            and e.type in ("person", "doorbell", "motion")
            and 0 <= (e.at - d.at).total_seconds() <= delivery_grace_minutes * 60
            for e in events
        )
        waited = (ref_now - d.at).total_seconds() / 60.0
        if not retrieved and waited >= delivery_grace_minutes:
            anomalies.append(
                Anomaly(
                    code="UNRETRIEVED_DELIVERY",
                    severity="warn",
                    title="A delivery hasn't been picked up",
                    detail=(
                        f"A package arrived at {_fmt(d.at)} and is still at the "
                        f"{d.zone.replace('_', ' ')} {int(waited)} minutes later."
                    ),
                    zone=d.zone,
                    at=d.at,
                )
            )

    # --- Rule 4: repeated night activity ------------------------------------
    night = [
        e for e in events
        if baseline.quiet_start_minute <= e.minutes_into_day < baseline.quiet_end_minute
        and e.type == "motion"
    ]
    if len(night) >= night_activity_threshold:
        zones = ", ".join(sorted({e.zone.replace('_', ' ') for e in night}))
        anomalies.append(
            Anomaly(
                code="REPEATED_NIGHT_ACTIVITY",
                severity="warn",
                title="Restless night",
                detail=(
                    f"{len(night)} movements during the quiet hours ({zones}). "
                    f"That's more than a typical night."
                ),
                zone=night[0].zone,
                at=night[0].at,
            )
        )

    # When a restless night is summarised as one alert, suppress the individual
    # warn-level off-hours motion alerts it already covers — a calm view shows one
    # clear message, not a stack. Critical off-hours alerts (a door/doorbell/person
    # at night) always survive; those genuinely need the caregiver's eyes.
    if any(a.code == "REPEATED_NIGHT_ACTIVITY" for a in anomalies):
        anomalies = [
            a for a in anomalies
            if not (a.code == "OFF_HOURS_ACTIVITY" and a.severity == "warn")
        ]

    # De-duplicate identical codes+zones (e.g. several off-hours motions in one zone
    # collapse to the most severe single alert to keep the caregiver view calm).
    anomalies = _dedupe(anomalies)

    return DayResult(
        is_all_well=len(anomalies) == 0,
        anomalies=anomalies,
        events_considered=len(events),
        zones_active=zones_active,
    )


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _median(values: List[int]) -> Optional[int]:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) // 2


def _minute_label(minute: Optional[int]) -> str:
    if minute is None:
        return "—"
    h = (minute // 60) % 24
    m = minute % 60
    ap = "AM" if h < 12 else "PM"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{m:02d} {ap}"


def _event_phrase(ev: Event) -> str:
    phrases = {
        "doorbell": f"The {ev.zone.replace('_', ' ')} doorbell rang",
        "person": f"A person was detected at the {ev.zone.replace('_', ' ')}",
        "motion": f"Motion in the {ev.zone.replace('_', ' ')}",
        "delivery": f"A delivery at the {ev.zone.replace('_', ' ')}",
    }
    return phrases.get(ev.type, f"{ev.type} in the {ev.zone.replace('_', ' ')}")


def _dedupe(anomalies: List[Anomaly]) -> List[Anomaly]:
    order = {"info": 0, "warn": 1, "critical": 2}
    best: Dict[tuple, Anomaly] = {}
    for a in anomalies:
        key = (a.code, a.zone)
        if key not in best or order[a.severity] > order[best[key].severity]:
            best[key] = a
    # keep original-ish ordering: critical first, then warn, then info
    return sorted(best.values(), key=lambda a: -order[a.severity])
