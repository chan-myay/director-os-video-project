from __future__ import annotations

import re

from app.burmese.converters.base import ConversionResult, ZawgyiConverter


CONSONANT = "\u1000-\u1021"
MEDIAL = "\u103b-\u103e"

ZAWGYI_CODEPOINT_MAP = {
    "\u103b": "\u103c",
    "\u103c": "\u103d",
    "\u106a": "\u1009",
    "\u106b": "\u100a",
    "\u108f": "\u1014",
    "\u1090": "\u101b",
    "\u1086": "\u103f",
    "\u1033": "\u102f",
    "\u1034": "\u1030",
    "\u1094": "\u1037",
    "\u1095": "\u1037",
    "\u1087": "\u103e",
    "\u1088": "\u103eု",
    "\u1089": "\u103eူ",
    "\u107e": "\u103c",
    "\u107f": "\u103c",
    "\u1080": "\u103c",
    "\u1081": "\u103c",
    "\u1082": "\u103c",
    "\u1083": "\u103c",
    "\u1084": "\u103c",
}


class LocalRuleZawgyiConverter(ZawgyiConverter):
    engine = "director_os_local_rule_zawgyi_converter"
    version = "1.0.3"

    def available(self) -> bool:
        return True

    def convert(self, text: str, confidence: float = 0.0) -> ConversionResult:
        converted = text
        warnings: list[str] = []
        for source, target in ZAWGYI_CODEPOINT_MAP.items():
            converted = converted.replace(source, target)

        converted = _reorder_leading_medials(converted)
        converted = _reorder_prebase_e(converted)
        converted = _fix_probable_asat(converted)
        converted = _dedupe_marks(converted)

        changed = converted != text
        status = "converted_validated" if changed else "conversion_needs_review"
        if not changed:
            warnings.append("HIGH_CONFIDENCE_ZAWGYI_UNCHANGED")
        return ConversionResult(
            source=text,
            converted=converted,
            detector="director_os_detector",
            detector_version="1.0.3",
            engine=self.engine,
            engine_version=self.version,
            status=status,
            confidence=confidence,
            warnings=warnings,
            changed=changed,
        )


def _reorder_prebase_e(text: str) -> str:
    pattern = re.compile(f"\u1031([{CONSONANT}])([{MEDIAL}]*)")
    previous = None
    current = text
    while previous != current:
        previous = current
        current = pattern.sub(lambda m: m.group(1) + m.group(2) + "\u1031", current)
    return current


def _reorder_leading_medials(text: str) -> str:
    pattern = re.compile(f"(^|[\\s\u1031])([{MEDIAL}]+)([{CONSONANT}])")
    previous = None
    current = text
    while previous != current:
        previous = current
        current = pattern.sub(lambda m: m.group(1) + m.group(3) + m.group(2), current)
    return current


def _fix_probable_asat(text: str) -> str:
    # Zawgyi lyrics often use U+1039 where Unicode expects asat U+103A.
    # Keep true stacking only for the most obvious virama-consonant clusters.
    text = re.sub(f"([{CONSONANT}])\u103a(?=[{CONSONANT}])", lambda m: m.group(1) + "\u103b", text)
    text = re.sub(f"([{CONSONANT}])\u1039(?=\\s|$|[{CONSONANT}]|\u1038)", lambda m: m.group(1) + "\u103a", text)
    return text


def _dedupe_marks(text: str) -> str:
    for mark in ["\u102c", "\u102d", "\u102e", "\u1032", "\u1036", "\u1037", "\u1038"]:
        text = re.sub(f"{mark}+", mark, text)
    return text
