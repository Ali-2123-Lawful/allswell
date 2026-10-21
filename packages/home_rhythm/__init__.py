"""
home-rhythm
===========

Turn a stream of home-sensor events (motion, person, doorbell, delivery) into a
daily-rhythm baseline and detect anomalies against it.

This package is deliberately dependency-free and framework-agnostic so it can be
reused by any project. It is the open-source core extracted from Allswell.

Core idea: a caregiver does not want to watch a live feed. They want to know the
normal day happened. Feed this module the last N days of events; it learns what
"normal" looks like per zone, then tells you whether today fits that pattern.

Typical use:

    from home_rhythm import Event, build_baseline, evaluate_day

    history = [Event(...), ...]          # previous days
    today = [Event(...), ...]            # today's events so far
    baseline = build_baseline(history)
    result = evaluate_day(today, baseline)
    for a in result.anomalies:
        print(a.severity, a.title, a.detail)
"""

from .engine import build_baseline, evaluate_day
from .model import Anomaly, Baseline, DayResult, Event

__all__ = [
    "Event",
    "Anomaly",
    "Baseline",
    "DayResult",
    "build_baseline",
    "evaluate_day",
]

__version__ = "0.1.0"
