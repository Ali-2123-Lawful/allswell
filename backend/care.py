"""
Care-companion tools
====================

The questions a caregiver actually asks, answered from the home_rhythm engine
and the digest layer. The dashboard API, the MCP server and the simulated Alexa+
experience all call these same functions, so every surface gives the same answer.

The demo models one household, so `person` is echoed back rather than looked up.
"""

from __future__ import annotations

from datetime import datetime

from packages.home_rhythm import build_baseline, evaluate_day

from . import events, seed
from .digest import make_digest

# Current demo scenario (what "today" looks like). Changeable live.
_state = {"scenario": "normal", "checked_in_at": None}


def load_scenario(scenario: str) -> None:
    """Replace the event stream with a scripted scenario (a week of history plus
    "today") and clear any earlier check-in."""
    events.load(seed.history_events(days=7) + seed.today_events(scenario))
    _state["scenario"] = scenario
    _state["checked_in_at"] = None


def snapshot() -> dict:
    """Evaluate today against the learned rhythm: everything any surface needs."""
    all_events = events.all_events()
    if not all_events:
        load_scenario(_state["scenario"])
        all_events = events.all_events()

    today = datetime.now().date()
    history = [e for e in all_events if e.at.date() < today]
    todays = [e for e in all_events if e.at.date() == today]

    baseline = build_baseline(history)
    # Evaluate as if it's early afternoon, so "missing morning" can fire in demos.
    now_ref = datetime.now().replace(hour=13, minute=0, second=0, microsecond=0)
    result = evaluate_day(todays, baseline, now=now_ref)

    return {
        "scenario": _state["scenario"],
        "digest": make_digest(result, baseline),
        "is_all_well": result.is_all_well,
        "anomalies": [
            {
                "code": a.code,
                "severity": a.severity,
                "title": a.title,
                "detail": a.detail,
                "zone": a.zone,
            }
            for a in result.anomalies
        ],
        "timeline": [
            {
                "type": e.type,
                "zone": e.zone,
                "at": e.at.isoformat(),
                "time_label": e.at.strftime("%I:%M %p").lstrip("0"),
                "subtype": e.subtype,
            }
            for e in sorted(todays, key=lambda x: x.at)
        ],
        "baseline": {
            "days_observed": baseline.days_observed,
            "zones": sorted(baseline.zones.keys()),
            # Per-zone usual window and the quiet hours, for the day-rhythm chart.
            "profiles": {
                zone: {
                    "first_minute": prof.typical_first_minute,
                    "last_minute": prof.typical_last_minute,
                    "days_seen": prof.days_seen,
                }
                for zone, prof in baseline.zones.items()
            },
            "quiet_start_minute": baseline.quiet_start_minute,
            "quiet_end_minute": baseline.quiet_end_minute,
        },
        "now_minute": now_ref.hour * 60 + now_ref.minute,
        "checked_in_at": _state["checked_in_at"],
    }


def get_day_status(person: str = "Mum") -> dict:
    """All's well, or needs a look — with the plain-language digest."""
    s = snapshot()
    return {
        "person": person,
        "is_all_well": s["is_all_well"],
        "headline": s["digest"]["headline"],
        "message": s["digest"]["message"],
        "digest_source": s["digest"]["source"],
        "checked_in_at": s["checked_in_at"],
    }


def get_rhythm_timeline(person: str = "Mum") -> dict:
    """Today's home-activity events, oldest first. Metadata only, never video."""
    return {"person": person, "events": snapshot()["timeline"]}


def get_anomalies(person: str = "Mum") -> dict:
    """What broke the normal rhythm today (empty when all is well)."""
    return {"person": person, "anomalies": snapshot()["anomalies"]}


def check_in(person: str = "Mum") -> dict:
    """Record that the caregiver reached out. A mock call: no video, ever."""
    _state["checked_in_at"] = datetime.now().isoformat()
    return {"person": person, "ok": True, "checked_in_at": _state["checked_in_at"]}
