"""
Verifier agent — applies procurement policies deterministically.
No LLM is used here. Rules are loaded from policies.yaml.
"""
from pathlib import Path

import yaml

_POLICY_PATH = Path(__file__).resolve().parent.parent.parent / "policies.yaml"
_policy_cache: dict | None = None


def _load_policies() -> dict:
    global _policy_cache
    if _policy_cache is None:
        with open(_POLICY_PATH, encoding="utf-8") as fh:
            _policy_cache = yaml.safe_load(fh)
    return _policy_cache


def check_candidate(
    candidate: dict,
    current_unit_price: float,
    stockout_days: int,
    needed_units: int,
    confidence: float,
) -> dict:
    """
    Apply procurement policies to a candidate supplier for a given order.

    Returns a dict with keys:
        decision: "APPROVED" | "REJECTED" | "ESCALATE"
        reason:   human-readable explanation
    """
    p = _load_policies()
    min_conf: float = p["min_confidence"]
    max_order: int = p["max_order_units"]
    max_lead: int = p["max_lead_time_days"]
    max_premium_pct: float = p["max_unit_price_premium_pct"]

    # Rule 1: confidence too low -> ESCALATE
    if confidence < min_conf:
        return {
            "decision": "ESCALATE",
            "reason": (
                f"Confidence {confidence:.2f} is below the minimum threshold {min_conf:.2f}. "
                "Requires human review."
            ),
        }

    # Rule 2: order size exceeds escalation threshold -> ESCALATE
    if needed_units > max_order:
        return {
            "decision": "ESCALATE",
            "reason": (
                f"Order size {needed_units:,} units exceeds escalation threshold "
                f"{max_order:,} units. Requires human approval."
            ),
        }

    # Rule 3: lead time too long -> REJECTED
    lead = candidate.get("lead_time_days", 0)
    if lead > max_lead:
        return {
            "decision": "REJECTED",
            "reason": (
                f"Lead time {lead}d exceeds policy maximum {max_lead}d."
            ),
        }

    # Rule 4: price premium too high -> REJECTED
    price = candidate.get("unit_price_inr", 0.0)
    ceiling = current_unit_price * (1 + max_premium_pct / 100)
    if price > ceiling:
        return {
            "decision": "REJECTED",
            "reason": (
                f"Unit price ₹{price:.2f} exceeds the {max_premium_pct}% premium ceiling "
                f"of ₹{ceiling:.2f} over current ₹{current_unit_price:.2f}."
            ),
        }

    if candidate["lead_time_days"] > stockout_days:
        return {
            "decision": "REJECTED",
            "reason": f"Arrives in {candidate['lead_time_days']} days, after stockout in {stockout_days} days",
        }

    # All checks passed -> APPROVED
    return {
        "decision": "APPROVED",
        "reason": (
            f"Candidate meets all policy criteria: "
            f"lead={lead}d (<={max_lead}d), "
            f"price=₹{price:.2f} (<={ceiling:.2f})."
        ),
    }
