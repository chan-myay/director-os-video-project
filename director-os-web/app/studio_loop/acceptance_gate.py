from __future__ import annotations

from app.studio_loop.approval_gate import consolidated_approval


def evaluate_acceptance(evaluation: dict, defects: list[dict]) -> dict:
    critical = [item["code"] for item in defects if item["severity"] == "critical"]
    approvals = consolidated_approval(defects)
    if not critical and not approvals:
        status = "acceptance_passed"
        next_action = "Review final preview."
    elif approvals:
        status = "awaiting_approval"
        next_action = approvals[0]["summary"]
    else:
        status = "stopped_with_blockers"
        next_action = "Review critical defects and repair options."
    return {
        "status": status,
        "score": evaluation.get("score", 0),
        "critical_failures": critical,
        "approvals_required": approvals,
        "next_action": next_action,
    }
