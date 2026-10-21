"""
Digest layer — turns a DayResult into warm, plain-language text for the caregiver.

Two backends:
  * Amazon Bedrock (optional, off by default) when ALLSWELL_USE_BEDROCK=1 and
    credentials are present. A small, cheap model is enough.
  * A templated fallback that runs at zero cost and with no network, so the app
    always works for development and for a safe demo.

The flow is deliberately multi-step (not a single prompt): we first build a
structured summary of the day from the rhythm engine, then ask the model to
phrase the "all's well" note or explain the anomaly, so the model only ever
rewords facts the engine already established.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Dict, Optional

from packages.home_rhythm import Baseline, DayResult

log = logging.getLogger(__name__)


def _structured_summary(result: DayResult, baseline: Baseline) -> dict:
    """Step 1: compress the day into a compact, model-friendly fact sheet."""
    return {
        "all_well": result.is_all_well,
        "events_considered": result.events_considered,
        "zones_active": result.zones_active,
        "days_of_history": baseline.days_observed,
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
    }


def _fallback_text(summary: dict) -> dict:
    """Zero-cost phrasing that is still genuinely useful."""
    if summary["all_well"]:
        zones = summary["zones_active"]
        zone_phrase = ", ".join(z.replace("_", " ") for z in zones) if zones else "the usual areas"
        return {
            "status": "ok",
            "headline": "All's well today",
            "message": (
                f"The day is following its normal rhythm. Activity in {zone_phrase} "
                f"looks like a typical day, based on the last {summary['days_of_history']} days. "
                f"Nothing needs your attention."
            ),
            "source": "template",
        }
    top = max(
        summary["anomalies"],
        key=lambda a: {"info": 0, "warn": 1, "critical": 2}.get(a["severity"], 0),
    )
    return {
        "status": top["severity"],
        "headline": top["title"],
        "message": top["detail"],
        "source": "template",
    }


def _bedrock_text(summary: dict) -> Optional[dict]:
    """Step 2 (optional): ask Bedrock to phrase it. Returns None on any failure
    so the caller can fall back cleanly."""
    try:
        # Imported lazily so the app runs without the AWS extras installed.
        # Signs requests with the standard AWS credential chain (env vars,
        # ~/.aws/credentials, SSO profile, ...).
        from anthropic import AnthropicBedrockMantle

        region = os.getenv("AWS_REGION", "us-east-1")
        model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-haiku-5-5")
        client = AnthropicBedrockMantle(aws_region=region)

        tone = (
            "Write a single calm, reassuring sentence for a family caregiver "
            "telling them their parent's day is following its normal pattern. "
            "Do not invent details beyond the facts."
            if summary["all_well"]
            else "Write one clear, non-alarming sentence for a family caregiver "
            "explaining what broke the normal pattern, using only the facts given. "
            "State what happened and when. Do not speculate about causes."
        )
        prompt = (
            f"{tone}\n\nFacts (JSON):\n{json.dumps(summary)}\n\n" "Respond with only the sentence."
        )

        resp = client.messages.create(
            model=model_id,
            max_tokens=1024,
            output_config={"effort": "low"},  # one plain sentence; little thinking needed
            messages=[{"role": "user", "content": prompt}],
        )
        if resp.stop_reason == "refusal":
            return None
        text = "".join(b.text for b in resp.content if b.type == "text").strip()
        if not text:
            return None

        if summary["all_well"]:
            return {
                "status": "ok",
                "headline": "All's well today",
                "message": text,
                "source": "bedrock",
            }
        top = max(
            summary["anomalies"],
            key=lambda a: {"info": 0, "warn": 1, "critical": 2}.get(a["severity"], 0),
        )
        return {
            "status": top["severity"],
            "headline": top["title"],
            "message": text,
            "source": "bedrock",
        }
    except Exception as exc:
        log.warning("Bedrock digest failed, using template: %s", exc)
        return None


# Bedrock phrasings keyed by the day's facts. The dashboard polls every few
# seconds; this keeps usage to one model call per distinct day-state.
_bedrock_cache: Dict[str, dict] = {}


def make_digest(result: DayResult, baseline: Baseline) -> dict:
    """Public entry point. Tries Bedrock when enabled, always falls back safely."""
    summary = _structured_summary(result, baseline)
    if os.getenv("ALLSWELL_USE_BEDROCK", "0") == "1":
        key = json.dumps(summary, sort_keys=True)
        out = _bedrock_cache.get(key) or _bedrock_text(summary)
        if out is not None:
            _bedrock_cache[key] = out
            return out
    return _fallback_text(summary)
