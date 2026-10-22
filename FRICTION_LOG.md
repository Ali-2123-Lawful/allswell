# Friction log

Problems we actually hit while building Allswell for the Build, Ship, Shape:
Amazon Developer Hackathon (Alexa+ track, with the AWS Builder and Open Source
mini-challenges). Each entry follows the hackathon's format.

| # | Entry | Severity |
|---|---|---|
| 1 | [Ring API test token from India](#1-ring-api-test-token-from-india) | High |
| 2 | [MCP SDK release vs required spec version](#2-mcp-sdk-release-vs-required-spec-version) | Medium |
| 3 | [Bedrock access still settling after it was enabled](#3-bedrock-access-still-settling-after-it-was-enabled) | Medium |
| 4 | [MCP Inspector: Server ID and cloned URL](#4-mcp-inspector-server-id-and-cloned-url) | Low |
| 5 | [Ring Access Tokens page returns 404](#5-ring-access-tokens-page-returns-404) | Low |

---

## 1. Ring API test token from India

- **Task:** Get a test token for the Ring Partner API, so the app could read Ring events at runtime.
- **Steps taken:** Read the Ring developer documentation (Getting Started, Development Guide, API Documentation). Registration asks for organisation details and government-ID verification; testing means linking a Ring account through "Log in with Ring".
- **Expected:** A hardware-free sandbox or test token, so a developer can make a first API call, as the hackathon's Ring track ("APIs, SDKs, simulators") suggests.
- **Actual:** Staging requires a Ring account with a device located in the US and an active Ring Protection plan. The Getting Started page mentions a sandbox with synthetic devices and events but doesn't say how to access it. We could not get a token from India.
- **Severity:** High (it blocked the track; we moved to Alexa+).
- **Workaround:** Built a local emulator of the endpoints we needed, then moved to the Alexa+ track and kept the same product.
- **Suggestion:** Document how to reach the synthetic-device sandbox, offer a hardware-free test token to hackathon participants, and state the US-device requirement in the hackathon's Ring track description.

## 2. MCP SDK release vs required spec version

- **Task:** Build a self-hosted MCP server implementing spec 2025-11-25 over Streamable HTTP with the official Python SDK.
- **Steps taken:** Ran `pip install mcp`, which installed 2.3.0, then checked `mcp.types.LATEST_PROTOCOL_VERSION`.
- **Expected:** The latest SDK targets the spec the hackathon requires, or a clear table maps SDK releases to spec versions.
- **Actual:** 2.3.0 defaults to protocol 2026-07-28. Release 1.30.0 targets 2025-11-25, but installing it next to our pinned FastAPI 0.115.5 failed dependency resolution (Starlette version range), which forced a FastAPI upgrade to 0.158.2.
- **Severity:** Medium.
- **Workaround:** Pinned `mcp==1.30.0`, upgraded FastAPI, and confirmed the negotiated version with a client smoke test (`scripts/mcp_smoke_test.py` prints `protocol 2025-11-25`).
- **Suggestion:** Publish a table of SDK releases and the spec version each targets, and clarify in the hackathon rules whether 2026-07-28 counts as "a later version, once confirmed".

## 3. Bedrock access still settling after it was enabled

- **Task:** Call Claude on Amazon Bedrock with a newly issued Bedrock API key.
- **Steps taken:** Our admin enabled the model and issued a Bedrock API key. The app called `InvokeModel` through boto3 with the inference profile `us.anthropic.claude-sonnet-4-5-20250929-v1:0` in us-east-1.
- **Expected:** Once access is granted, every call succeeds.
- **Actual:** The first call succeeded. A call moments later failed with `ResourceNotFoundException`: "Model use case details have not been submitted for this account. Fill out the Anthropic use case details form before using the model. If you have already filled out the form, try again in 15 minutes." Later calls succeeded.
- **Severity:** Medium.
- **Workaround:** Fall back to a template on any error, cache only successful results, and retry on the next request.
- **Suggestion:** Show the propagation status in the console after the use-case form is submitted, and make the error say that access is still being set up when the form has already been filed.

## 4. MCP Inspector: Server ID and cloned URL

- **Task:** Connect MCP Inspector to our local MCP server.
- **Steps taken:** Ran `npx @modelcontextprotocol/inspector`, cloned the example Streamable HTTP server in the new server-list UI, and edited it.
- **Expected:** A short form asking for transport and URL.
- **Actual:** The form asked for a "Server ID" with no explanation of what it is, and the cloned entry kept the example's remote URL (`https://example-server.modelcontextprotocol.io/mcp`), which is easy to miss.
- **Severity:** Low.
- **Workaround:** Typed any ID and replaced the URL with `http://127.0.0.1:8000/mcp` by hand.
- **Suggestion:** Explain the Server ID field inline (or default it from the URL), clear the URL when cloning, or add an "Add local server" shortcut.

## 5. Ring Access Tokens page returns 404

- **Task:** Read how Ring API access tokens work (lifetime, refresh).
- **Steps taken:** Opened `developer.amazon.com/docs/ring/access-tokens.html`, which search results listed.
- **Expected:** The Access Tokens documentation page.
- **Actual:** HTTP 404. The token lifetimes (about 4 hours for access tokens, about 30 days for refresh tokens) were only findable inside the very long API Documentation page.
- **Severity:** Low.
- **Workaround:** Searched the API Documentation page instead.
- **Suggestion:** Restore the page or redirect the old URL to the right section.
