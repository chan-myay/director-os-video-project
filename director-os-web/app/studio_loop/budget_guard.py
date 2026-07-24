from __future__ import annotations


def budget_guard() -> dict:
    return {
        "status": "no_spend",
        "cloud_calls_allowed": False,
        "paid_api_allowed": False,
        "model_download_allowed": False,
        "reason": "No explicit spend/upload/model approval was provided.",
    }
