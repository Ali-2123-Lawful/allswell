# Feature requests

Requests that came out of building Allswell for the Build, Ship, Shape: Amazon
Developer Hackathon. Each one has a description, why it matters to this
project, and a priority (Critical / Important / Nice-to-have). The problems
behind them are written up in the [friction log](FRICTION_LOG.md).

| # | Request | Priority |
|---|---|---|
| 1 | [Hardware-free Ring sandbox token](#1-hardware-free-ring-sandbox-token) | Critical |
| 2 | [Connect a self-hosted MCP server to a real Alexa+ for testing](#2-connect-a-self-hosted-mcp-server-to-a-real-alexa-for-testing) | Important |
| 3 | [SDK-to-spec version table for MCP](#3-sdk-to-spec-version-table-for-mcp) | Important |
| 4 | [Per-model code snippet in the Bedrock console](#4-per-model-code-snippet-in-the-bedrock-console) | Nice-to-have |

---

## 1. Hardware-free Ring sandbox token

- **Description:** A test token for a synthetic Ring home, available without a physical device or a Ring Protection plan, and to developers outside the US.
- **Why it matters:** We could not build on Ring at all from India, so Allswell moved to the Alexa+ track. Caretaking is a Ring priority category, and it needs event data (motion, doorbell, deliveries) far more than video.
- **Priority:** Critical

## 2. Connect a self-hosted MCP server to a real Alexa+ for testing

- **Description:** A documented way to attach a developer's MCP server to an Alexa+ device or simulator and talk to it end to end.
- **Why it matters:** We had to simulate the Alexa+ experience. Real end-to-end testing would let a caregiver actually ask Alexa "How was Mum's day?" and hear Allswell's answer.
- **Priority:** Important

## 3. SDK-to-spec version table for MCP

- **Description:** A table of official MCP SDK releases and the MCP spec version each one targets.
- **Why it matters:** The hackathon requires spec 2025-11-25, but the newest Python SDK targets 2026-07-28. Finding the right release took investigation and forced a framework upgrade.
- **Priority:** Important

## 4. Per-model code snippet in the Bedrock console

- **Description:** For each enabled model, show the exact model or inference-profile ID and a working call.
- **Why it matters:** Choosing between base model IDs, inference profiles and SDK clients took reading that a ready-made snippet would have saved.
- **Priority:** Nice-to-have
