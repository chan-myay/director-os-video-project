from __future__ import annotations

from app.burmese.converters.conversion_validator import validate_conversion
from app.burmese.converters.fallback_converter import LocalRuleZawgyiConverter
from app.burmese.converters.icu_zawgyi_converter import ICUZawgyiConverter
from app.burmese.converters.pyicu_adapter import PyICUZawgyiConverter


def zawgyi_to_unicode(text: str, confidence: float = 0.0) -> dict:
    converter = active_converter()
    result = converter.convert(text, confidence=confidence)
    validation = validate_conversion(text, result.converted, expected_zawgyi=True)
    status = result.status
    warnings = list(result.warnings) + validation["warnings"]
    if validation["result"] != "valid" and status == "converted_validated":
        status = "conversion_needs_review"
    return {
        "converted": result.converted,
        "changed": result.changed,
        "converter": result.engine,
        "converter_version": result.engine_version,
        "status": status,
        "uncertain": status != "converted_validated",
        "warnings": warnings,
        "validation": validation,
        "detector": result.detector,
        "detector_version": result.detector_version,
    }


def active_converter():
    for converter in [ICUZawgyiConverter(), PyICUZawgyiConverter(), LocalRuleZawgyiConverter()]:
        if converter.available():
            return converter
    return LocalRuleZawgyiConverter()


def converter_status() -> dict:
    converters = [ICUZawgyiConverter(), PyICUZawgyiConverter(), LocalRuleZawgyiConverter()]
    return {
        "active": active_converter().engine,
        "converters": [
            {"engine": converter.engine, "version": converter.version, "available": converter.available()}
            for converter in converters
        ],
        "pyicu_install_plan": {
            "package": "PyICU",
            "execution": "not_installed_by_this_patch",
            "requires": "local ICU development libraries/build tooling",
            "status": "prepared_only",
        },
    }
