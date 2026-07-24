from __future__ import annotations

import json
from typing import Any


class ValidationError(ValueError):
    pass


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:]
    decoder = json.JSONDecoder()
    start = text.find("{")
    if start == -1:
        raise ValidationError("No JSON object found in provider response.")
    last_error = None
    for index in range(start, len(text)):
        if text[index] != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError as exc:
            last_error = exc
            continue
        if isinstance(value, dict):
            return value
        raise ValidationError("Provider response is not a JSON object.")
    if last_error:
        raise ValidationError(f"Malformed JSON: {last_error}") from last_error
    raise ValidationError("No JSON object found in provider response.")


def validate_stage_response(value: dict[str, Any], expected_stage: str) -> dict[str, Any]:
    required = ["stage", "summary", "confidence", "sources", "artifacts", "blockers", "data"]
    missing = [key for key in required if key not in value]
    if missing:
        raise ValidationError(f"Missing keys: {', '.join(missing)}")
    if value["stage"] != expected_stage:
        original_stage = value["stage"]
        value["stage"] = expected_stage
        if isinstance(value.get("data"), dict):
            value["data"]["original_provider_stage"] = original_stage
    if not isinstance(value["summary"], str) or not value["summary"].strip():
        raise ValidationError("Summary must be a non-empty string.")
    try:
        confidence = float(value["confidence"])
    except (TypeError, ValueError) as exc:
        raise ValidationError("Confidence must be numeric.") from exc
    if confidence < 0 or confidence > 1:
        raise ValidationError("Confidence must be between 0 and 1.")
    if not isinstance(value["sources"], list):
        raise ValidationError("Sources must be a list.")
    if not isinstance(value["artifacts"], list):
        raise ValidationError("Artifacts must be a list.")
    if not isinstance(value["blockers"], list):
        raise ValidationError("Blockers must be a list.")
    if not isinstance(value["data"], dict):
        raise ValidationError("Data must be an object.")
    value["confidence"] = confidence
    return value
