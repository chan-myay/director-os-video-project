from __future__ import annotations

import hashlib
import unicodedata


ZAWGYI_ONLY = set("ၐၑၒၓၔၕၚၛၜၝၞၟၺၻၼႅႆႇႈႉႊႋႌႍႎႏ႐႑႒႓႔႕")
COMBINING_MARKS = set("\u102b\u102c\u102d\u102e\u102f\u1030\u1031\u1032\u1036\u1037\u1038\u103b\u103c\u103d\u103e")


def validate_conversion(original: str, converted: str, expected_zawgyi: bool) -> dict:
    warnings: list[str] = []
    if any(char in ZAWGYI_ONLY for char in converted):
        warnings.append("REMAINING_ZAWGYI_ONLY_CODEPOINT")
    if converted != unicodedata.normalize("NFC", converted):
        warnings.append("NOT_NFC_NORMALIZED")
    if _has_duplicated_combining_marks(converted):
        warnings.append("DUPLICATED_COMBINING_MARK")
    if expected_zawgyi and original == converted:
        warnings.append("EXPECTED_ZAWGYI_BUT_OUTPUT_UNCHANGED")
    if _character_loss_ratio(original, converted) > 0.35:
        warnings.append("LARGE_CHARACTER_LOSS")
    if _expansion_ratio(original, converted) > 0.6:
        warnings.append("LARGE_CHARACTER_EXPANSION")
    result = "valid" if not warnings else "needs_review"
    return {
        "result": result,
        "warnings": warnings,
        "source_hash": hashlib.sha256(original.encode("utf-8")).hexdigest(),
        "converted_hash": hashlib.sha256(converted.encode("utf-8")).hexdigest(),
    }


def _has_duplicated_combining_marks(text: str) -> bool:
    previous = ""
    for char in text:
        if char == previous and char in COMBINING_MARKS:
            return True
        previous = char
    return False


def _character_loss_ratio(original: str, converted: str) -> float:
    if not original:
        return 0.0
    return max(0, len(original) - len(converted)) / len(original)


def _expansion_ratio(original: str, converted: str) -> float:
    if not original:
        return 0.0
    return max(0, len(converted) - len(original)) / len(original)
