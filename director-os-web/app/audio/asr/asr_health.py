from __future__ import annotations

from typing import Any

from app.audio.asr.mlx_whisper_adapter import MLXWhisperAdapter
from app.audio.asr.whisper_cli_adapter import WhisperCLIAdapter
from app.audio.asr.whisper_cpp_adapter import WhisperCppAdapter


def asr_health() -> dict[str, Any]:
    providers = [MLXWhisperAdapter().health(), WhisperCLIAdapter().health(), WhisperCppAdapter().health()]
    return {
        "available": any(item["available"] for item in providers),
        "providers": providers,
        "burmese_verified": False,
        "downloads_performed": False,
        "recommendation": local_asr_setup_context(),
    }


def local_asr_setup_context() -> dict[str, Any]:
    return {
        "primary": {
            "tool": "mlx-whisper",
            "model": "small or medium multilingual Whisper model, only after approval",
            "official_source": "https://github.com/ml-explore/mlx-examples/tree/main/whisper",
            "license": "MIT for MLX examples; model license must be reviewed before download",
            "download_size": "model-dependent; not downloaded",
            "disk_use": "model-dependent",
            "expected_memory": "unknown until selected model benchmark",
            "burmese_support": "must be verified by non-private test audio before claims",
            "commands": [["python", "-m", "pip", "install", "mlx-whisper"]],
            "uninstall": "remove isolated environment/model files selected during approval",
        },
        "fallback": {
            "tool": "whisper.cpp",
            "model": "small multilingual GGML/GGUF model, only after approval",
            "official_source": "https://github.com/ggerganov/whisper.cpp",
            "license": "MIT for code; model license must be reviewed before download",
            "download_size": "model-dependent; not downloaded",
            "disk_use": "model-dependent",
            "expected_memory": "unknown until selected model benchmark",
            "burmese_support": "must be verified by non-private test audio before claims",
            "commands": [["git", "clone", "--depth", "1", "https://github.com/ggerganov/whisper.cpp"]],
            "uninstall": "remove isolated checkout/model files selected during approval",
        },
    }
