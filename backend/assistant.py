"""
Simulated Alexa+ conversation
=============================

Turns a caregiver's question ("How was Mum's day?") into a call to one of the
Allswell MCP tools — made with the official MCP client over Streamable HTTP, the
same way a voice assistant would — and phrases the result as a short spoken reply.

Intent matching is deliberately simple keyword rules: the point of the
simulation is the tool flow, and every reply stays grounded in tool output.
"""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from datetime import datetime

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

_PEOPLE = r"\b(mum|mom|mother|mummy|dad|father|papa|grandma|grandpa|gran|nan|nana)\b"

# First match wins, so the more specific intents come first.
_INTENTS = [
    ("privacy", r"\b(camera|video|footage|live ?view|live feed|watch (her|him|them))\b"),
    ("check_in", r"\b(check[ -]?in|call|reach out)\b"),
    (
        "get_anomalies",
        r"\b(anything|should i know|worr\w*|wrong|alerts?|unusual|problems?|concern\w*)\b",
    ),
    (
        "get_rhythm_timeline",
        r"\b(timeline|what happened|what did|when did|events?|activity|this morning|so far)\b",
    ),
]

# Short answers to an offer ("Would you like me to check in on Mum?").
_AFFIRM = r"^(yes|yeah|yep|yup|sure|ok|okay|please|go ahead|do it)\b"
_DECLINE = r"^(no|nope|not now|no thanks|don'?t)\b"

# Conversation state per browser session: who the caregiver is asking about and
# any offer awaiting a yes/no. This is what lets follow-ups like "Yes" or
# "Anything I should know?" carry over from the previous turn.
_sessions: OrderedDict[str, dict] = OrderedDict()
_MAX_SESSIONS = 200

_EVENT_WORDS = {
    "motion": "movement",
    "person": "someone",
    "doorbell": "the doorbell",
    "delivery": "a delivery",
}


def _event_phrase(e: dict) -> str:
    zone = e["zone"].replace("_", " ")
    prep = "in" if e["type"] == "motion" and e["zone"] != "front_door" else "at"
    return f"{_EVENT_WORDS.get(e['type'], e['type'])} {prep} the {zone} at {e['time_label']}"


def _session(session_id: str) -> dict:
    """The conversation state for one browser session (oldest evicted first)."""
    state = _sessions.pop(session_id, None) or {"person": "Mum", "pending": None}
    _sessions[session_id] = state
    while len(_sessions) > _MAX_SESSIONS:
        _sessions.popitem(last=False)
    return state


def route(question: str, default_person: str = "Mum") -> tuple[str, str]:
    """Pick (intent, person) for a question. Defaults to the day status, and to
    the person from earlier in the conversation when none is named."""
    q = question.lower()
    m = re.search(_PEOPLE, q)
    person = m.group(1).capitalize() if m else default_person
    for intent, pattern in _INTENTS:
        if re.search(pattern, q):
            return intent, person
    return "get_day_status", person


async def call_tool(mcp_url: str, name: str, arguments: dict) -> dict:
    """One MCP round trip: initialize, call the tool, return its JSON result."""
    async with streamable_http_client(mcp_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments)
    if result.isError:
        raise RuntimeError(result.content[0].text)
    return json.loads(result.content[0].text)


def phrase(tool: str, person: str, data: dict) -> str:
    """Turn a tool result into one or two calm spoken sentences."""
    if tool == "get_day_status":
        if data["is_all_well"]:
            return f"Good news: all's well with {person} today. {data['message']}"
        return (
            f"Heads up: {data['headline'].lower()}. {data['message']} "
            f"Would you like me to check in on {person}?"
        )

    if tool == "get_anomalies":
        items = data["anomalies"]
        if not items:
            return f"Nothing unusual today. {person}'s day is following the normal rhythm."
        offer = f" Would you like me to check in on {person}?"
        if len(items) == 1:
            return f"One thing stands out. {items[0]['detail']}" + offer
        return f"{len(items)} things stand out. " + " ".join(a["detail"] for a in items) + offer

    if tool == "get_rhythm_timeline":
        events = data["events"]
        if not events:
            return f"I haven't seen any activity at {person}'s home yet today."
        parts = [_event_phrase(e) for e in events[:6]]
        more = f", and {len(events) - 6} more" if len(events) > 6 else ""
        return "So far today: " + ", ".join(parts) + more + "."

    if tool == "check_in":
        at = datetime.fromisoformat(data["checked_in_at"]).strftime("%I:%M %p").lstrip("0")
        return (
            f"Done. I've logged your check-in with {person} at {at}. "
            "I'll let you know if anything changes."
        )

    return json.dumps(data)


def _needs_a_look(tool: str, data: dict) -> bool:
    """Whether this result is worth offering a check-in for."""
    if tool == "get_day_status":
        return not data["is_all_well"]
    return tool == "get_anomalies" and bool(data["anomalies"])


async def ask(question: str, mcp_url: str, session_id: str = "default") -> dict:
    """Answer one caregiver question: pick a tool, call it over MCP, phrase the
    result. Returns the reply plus the tool call, which the UI shows as proof,
    and any offer ("check_in") the caregiver can accept with a plain "Yes"."""
    state = _session(session_id)
    q = question.strip().lower()
    short_answer = len(q.split()) <= 5

    if state["pending"] == "check_in" and short_answer and re.search(_DECLINE, q):
        state["pending"] = None
        return {
            "reply": "Okay. I'll keep watching the rhythm and tell you if anything else changes.",
            "tool": None,
            "offer": None,
        }
    if state["pending"] == "check_in" and short_answer and re.search(_AFFIRM, q):
        intent, person = "check_in", state["person"]
    else:
        intent, person = route(question, state["person"])

    tool = "get_day_status" if intent == "privacy" else intent
    arguments = {"person": person}
    data = await call_tool(mcp_url, tool, arguments)
    reply = phrase(tool, person, data)
    if intent == "privacy":
        reply = (
            "I can't show video. Allswell never uses a camera feed, only activity "
            "insights. Here's what I can tell you. " + reply
        )

    offer = "check_in" if _needs_a_look(tool, data) else None
    state.update(person=person, pending=offer)
    return {"reply": reply, "tool": tool, "arguments": arguments, "result": data, "offer": offer}
