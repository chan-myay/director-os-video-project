from __future__ import annotations

import shutil
import subprocess

from app.burmese.converters.base import ConversionResult, ZawgyiConverter


class ICUZawgyiConverter(ZawgyiConverter):
    engine = "icu_transliterator_Zawgyi-my"
    version = "system_icu_uconv"

    def available(self) -> bool:
        return shutil.which("uconv") is not None

    def convert(self, text: str, confidence: float = 0.0) -> ConversionResult:
        uconv = shutil.which("uconv")
        if not uconv:
            return ConversionResult(
                source=text,
                converted=text,
                detector="director_os_detector",
                detector_version="1.0.3",
                engine=self.engine,
                engine_version=self.version,
                status="conversion_failed",
                confidence=confidence,
                warnings=["UCONV_NOT_AVAILABLE"],
                changed=False,
            )
        result = subprocess.run(
            [uconv, "-x", "Zawgyi-my"],
            input=text,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return ConversionResult(
                source=text,
                converted=text,
                detector="director_os_detector",
                detector_version="1.0.3",
                engine=self.engine,
                engine_version=self.version,
                status="conversion_failed",
                confidence=confidence,
                warnings=["UCONV_FAILED", result.stderr.strip()],
                changed=False,
            )
        converted = result.stdout.rstrip("\n")
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
