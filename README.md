# Allswell

**Ask Alexa how Mum's day went — without ever watching her.**

Allswell is a privacy-first care companion for families with an older relative
living alone. It reads a stream of home-activity events — motion, person,
doorbell, delivery — learns that person's daily rhythm, and stays quiet unless
the rhythm breaks. The caregiver just asks *"How was Mum's day?"* and hears
*"All's well"*, or a calm, specific heads-up when something is off.
**No live video is ever shown to the caregiver.** Insights only; the privacy
inversion is the product.

Built for the **Alexa+ track** (care-taking) of the Build, Ship, Shape: Amazon
Developer Hackathon, with the **Open Source** mini-challenge.

---

## What it does

- **Quiet by default.** When the morning kitchen activity, the midday door and the
  quiet night all happen on schedule, the answer is simply "All's well today".
- **Speaks only on anomaly.** No morning routine by late morning · a doorbell at
  3 AM · a delivery left unretrieved · a restless night.
- **Answers out loud.** Allswell exposes its insights as **MCP tools**, so a voice
  assistant like Alexa+ can answer the caregiver's questions from real data.
- **Never shows footage.** Ask for the camera and Allswell declines and tells you
  what it *can* say instead. The caregiver sees event metadata (what, where,
  when) and plain-language summaries, nothing more.

---

## Quick start

No API keys, no AWS account, no hardware needed to run the full demo.

**macOS / Linux**

```bash
git clone <your-repo-url> allswell
cd allswell
./run.sh
```

**Windows (PowerShell)**

```powershell
git clone <your-repo-url> allswell
cd allswell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --port 8000
```

Then open:

| URL | What it is |
|---|---|
| <http://127.0.0.1:8000/ask> | **Simulated Alexa+ experience**: ask by voice or text |
| <http://127.0.0.1:8000> | Caregiver dashboard |
| `http://127.0.0.1:8000/mcp` | **MCP server** (Streamable HTTP) for Alexa+ or any MCP client |

Use the **Demo scenario** picker (on either page) to switch between a calm day
and each anomaly. The demo timeline is deterministic, so every run looks the same.

---

## How it uses Alexa+ technology

### 1. MCP server: the real integration

`backend/mcp_server.py` is a self-hosted **Model Context Protocol** server built
with the official MCP Python SDK (`mcp==1.30.0`), speaking **MCP spec version
2025-11-25** over the **Streamable HTTP** transport. It is mounted inside the app
at `/mcp` and exposes four tools:

| Tool | Returns |
|---|---|
| `get_day_status(person)` | all's well / needs a look, plus a plain-language digest |
| `get_rhythm_timeline(person)` | today's events (type, room, time), metadata only |
| `get_anomalies(person)` | what broke the normal rhythm today (empty when all is well) |
| `check_in(person)` | records that the caregiver reached out (a mock call; never video) |

The read-only tools carry `readOnlyHint` annotations. The server's instructions
tell the assistant to answer only from tool results and never speculate.

**Try it with the official client:**

```bash
.venv/bin/python scripts/mcp_smoke_test.py          # Windows: .\.venv\Scripts\python.exe scripts\mcp_smoke_test.py
```

```
connected to Allswell | protocol 2025-11-25
tools: get_day_status, get_rhythm_timeline, get_anomalies, check_in
```

**Or with the MCP Inspector** (needs Node.js):

```bash
npx @modelcontextprotocol/inspector
```

Add a server with transport **Streamable HTTP** and URL
`http://127.0.0.1:8000/mcp`, connect, then run any tool from the **Tools** tab.

### 2. Simulated Alexa+ experience: the demo surface

`/ask` is a conversational, voice-device-style web app, clearly labelled as a
simulation. The caregiver asks things like *"How was Mum's day?"*,
*"Anything I should know?"* or *"Check in on Mum"*, by typing or speaking.

Under the hood it behaves like a voice assistant would: `backend/assistant.py`
matches the question to a tool, then calls that tool **through the MCP client
over Streamable HTTP against the server above**, and phrases the result as a
short spoken reply. Each reply shows which MCP tool was called; click it to see
the raw tool result.

Voice input and spoken replies use the browser's Web Speech API (Chrome or
Edge). Note that Chrome sends speech audio to Google for transcription; typing
works everywhere and sends nothing anywhere.

Source: `frontend/ask.html`, `frontend/ask.js`, `backend/assistant.py`.

---

## Architecture

```
                                     ┌──▶ /api/state ──▶ caregiver dashboard
 home events ──▶ care.py ────────────┤
 (simulator)     home_rhythm engine  └──▶ /mcp  MCP server ◀── Alexa+ · MCP Inspector
                 + digest layer                    ▲
                                                   └── MCP client ◀── /ask (simulated Alexa+)
```

- `packages/home_rhythm/`: **dependency-free** rhythm baseline + anomaly engine
  (the Open Source mini-challenge piece).
- `backend/care.py`: the four care-companion tools as plain functions. The
  dashboard, the MCP server and the simulated Alexa+ all call these, so every
  surface gives the same answer.
- `backend/mcp_server.py`: MCP server (spec 2025-11-25, Streamable HTTP).
- `backend/assistant.py`: simulated Alexa+ (question → MCP tool call → reply).
- `backend/digest.py`: turns the verdict into a plain-language digest
  (zero-cost template by default; optional Amazon Bedrock phrasing).
- `backend/events.py` + `backend/seed.py`: in-memory event store and a
  deterministic week of history plus scripted anomaly scenarios.
- `backend/main.py`: FastAPI app wiring it all together.
- `frontend/`: the dashboard (`index.html`) and the Alexa+ simulation (`ask.html`).

**Where the events come from.** For the demo, a simulator generates a believable
week of activity for someone living alone, plus "today" for each scenario. The
engine doesn't care about the source: in production the same events could come
from smart doorbells, motion sensors or any home-sensor hub.

---

## The rhythm engine (anomaly rules)

| Rule | Fires when | Severity |
|------|------------|----------|
| `MISSING_MORNING_ROUTINE` | a reliable morning zone has no activity by the grace cutoff | critical |
| `OFF_HOURS_ACTIVITY` | motion / person / doorbell during the learned quiet window | critical / warn |
| `UNRETRIEVED_DELIVERY` | a delivery with no pickup activity within the grace window | warn |
| `REPEATED_NIGHT_ACTIVITY` | repeated night-time movement above a threshold | warn |

No ML, just rolling statistics and explainable rules, so every alert carries
the real event time and room.

### Using `home_rhythm` in your own project (Open Source mini-challenge)

`packages/home_rhythm/` has no third-party dependencies. Copy it into any
project that has timestamped home-sensor events:

```python
from home_rhythm import Event, build_baseline, evaluate_day

baseline = build_baseline(history_events)        # previous days
result = evaluate_day(todays_events, baseline)   # today so far
for a in result.anomalies:
    print(a.severity, a.title, a.detail)
```

---

## Optional: Amazon Bedrock phrasing

Set `ALLSWELL_USE_BEDROCK=1` in `.env` (copy `.env.example`), run
`pip install "anthropic[bedrock]"` (the Anthropic SDK's Bedrock client; it signs
requests with your AWS credentials via botocore), and
provide AWS credentials. The digest layer first builds a structured day summary
from the rhythm engine, then asks a small Bedrock model (Claude Haiku 5.5 by
default) to phrase the "all's well" note or explain the anomaly. That's a
multi-step flow, not a one-shot wrapper. Without Bedrock, a templated fallback
produces the same facts at zero cost; that is what the demo uses, and Bedrock is
off by default. If you enable it, usage is tiny; still, set a billing alert.

---

## Privacy

- No camera feed, video, image or audio from the home is ever collected or shown.
- Allswell only handles event metadata: event type, room and time.
- No tool returns media, and asking for video is declined by design.

---

## License

MIT — see [LICENSE](LICENSE).
