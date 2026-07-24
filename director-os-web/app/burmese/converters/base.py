from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversionResult:
    source: str
    converted: str
    detector: str
    detector_version: str
    engine: str
    engine_version: str
    status: str
    confidence: float
    warnings: list[str] = field(default_factory=list)
    changed: bool = False


class ZawgyiConverter:
    engine = "base"
    version = "0"

    def available(self) -> bool:
        return False

    def convert(self, text: str, confidence: float = 0.0) -> ConversionResult:
        return ConversionResult(
            source=text,
            converted=text,
            detector="unknown",
            detector_version="unknown",
            engine=self.engine,
            engine_version=self.version,
            status="conversion_failed",
            confidence=confidence,
            warnings=["BASE_CONVERTER_NOT_IMPLEMENTED"],
            changed=False,
        )
