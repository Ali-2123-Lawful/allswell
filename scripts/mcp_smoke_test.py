"""
MCP smoke test
==============

Connects to the Allswell MCP server with the official MCP Python client over
Streamable HTTP, prints the negotiated protocol version, lists the tools, and
calls each one.

Run from the repo root while the app is running:
    .venv/Scripts/python scripts/mcp_smoke_test.py     (Windows)
    .venv/bin/python scripts/mcp_smoke_test.py         (macOS / Linux)
"""

from __future__ import annotations

import asyncio
import json
import sys

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"


async def main() -> None:
    """Open a session, list the tools, call each one and print the results."""
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    async with streamable_http_client(URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"connected to {init.serverInfo.name} | protocol {init.protocolVersion}")

            tools = await session.list_tools()
            print("tools:", ", ".join(t.name for t in tools.tools))

            for name in ("get_day_status", "get_anomalies", "get_rhythm_timeline", "check_in"):
                result = await session.call_tool(name, {"person": "Mum"})
                body = result.structuredContent or result.content[0].text
                print(
                    f"\n{name} ->\n{json.dumps(body, indent=2) if isinstance(body, dict) else body}"
                )


if __name__ == "__main__":
    asyncio.run(main())
