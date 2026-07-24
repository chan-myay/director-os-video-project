from __future__ import annotations


def consolidated_approval(defects: list[dict]) -> list[dict]:
    needs = []
    if any(item["code"] in {"MODEL_UNAVAILABLE", "LOCAL_ASR_UNAVAILABLE"} for item in defects):
        needs.append(
            {
                "approval_type": "local_model_or_asr_setup",
                "summary": "Choose one local storyboard/ASR capability before final AI generation or trusted lyric alignment can pass.",
                "status": "pending",
            }
        )
    if any(item["code"] in {"AI_GENERATION_UNAVAILABLE", "LIPSYNC_PROVIDER_UNAVAILABLE"} for item in defects):
        needs.append(
            {
                "approval_type": "generation_provider_setup",
                "summary": "Approve a local model install or explicit private/cloud renderer before production AI frames or lip-sync can be created.",
                "status": "pending",
            }
        )
    return needs[:1]
