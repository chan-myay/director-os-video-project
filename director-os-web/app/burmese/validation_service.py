from __future__ import annotations


def validate_burmese_record(record: dict) -> list[str]:
    warnings = []
    if not record.get("original_text"):
        warnings.append("missing_original_text")
    if record.get("detected_encoding") == "uncertain":
        warnings.append("encoding_uncertain")
    if not record.get("caption_text"):
        warnings.append("missing_caption_text")
    return warnings
