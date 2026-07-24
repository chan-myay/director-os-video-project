from __future__ import annotations

import importlib.util

from app.burmese.converters.base import ConversionResult, ZawgyiConverter


class PyICUZawgyiConverter(ZawgyiConverter):
    engine = "pyicu_transliterator_Zawgyi-my"
    version = "PyICU"

    def available(self) -> bool:
        return importlib.util.find_spec("icu") is not None

    def convert(self, text: str, confidence: float = 0.0) -> ConversionResult:
        if not self.available():
            return ConversionResult(
                source=text,
                converted=text,
                detector="director_os_detector",
                detector_version="1.0.3",
                engine=self.engine,
                engine_version=self.version,
                status="conversion_failed",
                confidence=confidence,
                warnings=["PYICU_NOT_INSTALLED"],
                changed=False,
            )
        from icu import Transliterator  # type: ignore

        transliterator = Transliterator.createInstance("Zawgyi-my")
        converted = transliterator.transliterate(text)
        return ConversionResult(
            source=text,
            converted=converted,
            detector="director_os_detector",
            detector_version="1.0.3",
            engine=self.engine,
            engine_version=self.version,
            status="converted_validated" if converted != text else "conversion_needs_review",
            confidence=confidence,
            warnings=[] if converted != text else ["HIGH_CONFIDENCE_ZAWGYI_UNCHANGED"],
            changed=converted != text,
        )
