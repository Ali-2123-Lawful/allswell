"""
Allswell MCP server
===================

Exposes the care-companion tools over the Model Context Protocol (spec version
2025-11-25, Streamable HTTP transport) using the official MCP Python SDK, so a
voice assistant such as Alexa+ can answer "How was Mum's day?" from real data.

Mounted by backend/main.py at http://127.0.0.1:8000/mcp. Every tool wraps
backend/care.py — the same functions the dashboard uses — so the assistant and
the dashboard always agree. No tool ever returns video or images: insights only.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from . import care

server = FastMCP(
    "Allswell",
    instructions=(
        "Allswell is a privacy-first care companion. It watches the daily rhythm "
        "of an older relative's home through activity events only (never video) "
        "and tells the family caregiver whether today looks normal. Answer calmly "
        "and only from tool results; do not speculate about causes."
    ),
    stateless_http=True,
    json_response=True,
)

_READ_ONLY = ToolAnnotations(readOnlyHint=True, openWorldHint=False)


@server.tool(annotations=_READ_ONLY)
def get_day_status(person: str = "Mum") -> dict:
    """Is today following the person's normal daily rhythm? Returns all-well or
    needs-a-look, with a short plain-language summary for the caregiver."""
    return care.get_day_status(person)


@server.tool(annotations=_READ_ONLY)
def get_rhythm_timeline(person: str = "Mum") -> dict:
    """Today's home-activity events (type, room, time), oldest first. Event
    metadata only — there is no camera feed or video."""
    return care.get_rhythm_timeline(person)


@server.tool(annotations=_READ_ONLY)
def get_anomalies(person: str = "Mum") -> dict:
    """Anything that broke the normal rhythm today, e.g. a missing morning
    routine or a door at 3 AM. Empty when all is well."""
    return care.get_anomalies(person)


@server.tool(
    annotations=ToolAnnotations(readOnlyHint=False, idempotentHint=False, openWorldHint=False)
)
def check_in(person: str = "Mum") -> dict:
    """Record that the caregiver reached out to the person (a mock call in this
    demo). Never starts a camera or video stream."""
    return care.check_in(person)
