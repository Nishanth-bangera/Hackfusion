"""
Pipeline — Planner + Verifier + Executor stages.

The Planner is purely rule-based: no LLM, no retry loop.
(See README Limitations.)
"""
import json

from app.db import get_connection
from app.tools.db_tools import find_alternatives
from app.agents.verifier import check_candidate
from app.executor import execute_actions


def _get_current_price(product_id: int, disrupted_port: str) -> float:
    """Return the unit price the disrupted supplier charges for this product."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT sp.unit_price_inr
            FROM supplier_products sp
            JOIN suppliers s ON s.id = sp.supplier_id
            WHERE sp.product_id = ? AND s.port = ? AND s.approved = 1
            LIMIT 1
            """,
            (product_id, disrupted_port),
        ).fetchone()
        return row["unit_price_inr"] if row else 0.0
    finally:
        conn.close()


def _record_event(job_id: int, agent: str, message: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO job_events (job_id, agent, message) VALUES (?, ?, ?)",
            (job_id, agent, message),
        )
        conn.commit()
    finally:
        conn.close()


def _record_action(job_id: int, action_type: str, status: str, payload: dict) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO actions (job_id, action_type, status, payload_json) VALUES (?,?,?,?)",
            (job_id, action_type, status, json.dumps(payload)),
        )
        conn.commit()
    finally:
        conn.close()


def run_pipeline(
    job_id: int,
    impact,
    confidence: float,
    disrupted_port: str,
) -> dict:
    """
    For each exposure:
      1. Find alternative suppliers (find_alternatives, cheapest first).
      2. Check each candidate against procurement policies (Verifier).
      3. APPROVED -> Executor writes PO + email draft.
         ESCALATE -> recorded in actions, not auto-executed.
         REJECTED -> recorded in actions.

    Returns a summary dict for the outcome report.
    """
    approved_actions: list[dict] = []
    approved_count = 0
    escalated_count = 0
    rejected_count = 0
    total_approved_inr = 0.0

    for exposure in impact.exposures:
        product_id = exposure.product_id
        sku = exposure.sku
        order_id = exposure.order_id
        quantity = exposure.quantity
        stockout_days = exposure.stockout_days

        current_price = _get_current_price(product_id, disrupted_port)
        candidates = find_alternatives(product_id, exclude_port=disrupted_port)

        _record_event(
            job_id, "planner",
            f"Order {order_id} ({sku}): {len(candidates)} alternative(s) found, "
            f"stockout_days={stockout_days}, current_price=\u20b9{current_price:.2f}",
        )

        if not candidates:
            _record_event(
                job_id, "planner",
                f"Order {order_id} ({sku}): no alternatives found — escalating",
            )
            _record_action(job_id, "escalation", "escalated", {
                "order_id": order_id,
                "sku": sku,
                "reason": "No alternative suppliers found",
            })
            escalated_count += 1
            continue

        acted = False
        for candidate in candidates:
            result = check_candidate(
                candidate=candidate,
                current_unit_price=current_price,
                stockout_days=stockout_days,
                needed_units=quantity,
                confidence=confidence,
            )
            decision = result["decision"]
            reason = result["reason"]

            _record_event(
                job_id, "verifier",
                f"Order {order_id} ({sku}) via {candidate['supplier_name']}: "
                f"{decision} \u2014 {reason}",
            )

            if decision == "APPROVED":
                action = {
                    "order_id": order_id,
                    "supplier_name": candidate["supplier_name"],
                    "sku": sku,
                    "quantity": quantity,
                    "unit_price_inr": candidate["unit_price_inr"],
                    "lead_time_days": candidate["lead_time_days"],
                }
                approved_actions.append(action)
                total_approved_inr += quantity * candidate["unit_price_inr"]
                approved_count += 1
                acted = True
                break  # take first approved candidate (cheapest, due to ORDER BY)

            elif decision == "ESCALATE":
                _record_action(job_id, "escalation", "escalated", {
                    "order_id": order_id,
                    "sku": sku,
                    "candidate": candidate["supplier_name"],
                    "reason": reason,
                })
                escalated_count += 1
                acted = True
                break  # do not auto-execute escalations

            else:  # REJECTED
                _record_action(job_id, "escalation", "rejected", {
                    "order_id": order_id,
                    "sku": sku,
                    "candidate": candidate["supplier_name"],
                    "reason": reason,
                })
                rejected_count += 1
                # continue to next candidate

        if not acted:
            # All candidates were rejected — escalate
            _record_event(
                job_id, "planner",
                f"Order {order_id} ({sku}): all candidates rejected — escalating",
            )
            _record_action(job_id, "escalation", "escalated", {
                "order_id": order_id,
                "sku": sku,
                "reason": "All candidates rejected by procurement policy",
            })
            escalated_count += 1

    # --- Executor: write PO and email files for approved actions ---
    output_files: list[str] = []
    if approved_actions:
        output_files = execute_actions(job_id, approved_actions)
        _record_event(
            job_id, "executor",
            f"Wrote {len(output_files)} file(s) to outbox/",
        )

    return {
        "approved_pos": approved_count,
        "escalations": escalated_count,
        "rejections": rejected_count,
        "output_files": output_files,
        "total_approved_inr": total_approved_inr,
    }
