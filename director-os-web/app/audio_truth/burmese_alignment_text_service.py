from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any


BURMESE_START = "\u1000"
BURMESE_END = "\u109f"


def build_alignment_text_map(occurrences: list[dict[str, Any]], tokenizer_vocab: dict[str, int] | None = None) -> dict[str, Any]:
    vocab = tokenizer_vocab or {}
    phrase_maps = []
    unsupported_total = 0
    for occurrence in occurrences:
        display = occurrence["canonical_unicode_lyric"]
        normalized = unicodedata.normalize("NFC", display)
        acoustic, transformations = acoustic_text(normalized)
        graphemes = list(acoustic)
        tokens = []
        unsupported = []
        for char in graphemes:
            token_id = vocab.get(char)
            tokens.append({"text": char, "token_id": token_id, "supported": token_id is not None or not is_burmese(char)})
            if token_id is None and is_burmese(char):
                unsupported.append(char)
        unsupported_total += len(unsupported)
        phrase_maps.append(
            {
                "occurrence_id": occurrence["occurrence_id"],
                "display_text": display,
                "normalized_display_text": normalized,
                "acoustic_alignment_text": acoustic,
                "grapheme_sequence": graphemes,
                "syllable_like_sequence": syllable_like(acoustic),
                "tokenizer_sequence": tokens,
                "unsupported_characters": sorted(set(unsupported)),
                "transformations": transformations,
                "reversible_mapping": "display_text retained; acoustic text used only for alignment scoring",
            }
        )
    return {
        "version": "audio-truth-v3",
        "phrase_count": len(phrase_maps),
        "unsupported_character_count": unsupported_total,
        "phrases": phrase_maps,
    }


def acoustic_text(text: str) -> tuple[str, list[str]]:
    transformations = []
    out = []
    for char in text:
        category = unicodedata.category(char)
        if category.startswith("P") or char in {"…", "“", "”", "'", '"'}:
            transformations.append(f"removed_unsung_punctuation:{char}")
            continue
        if category == "Cf":
            transformations.append(f"removed_invisible_format:{ord(char):04x}")
            continue
        out.append(char)
    compact = " ".join("".join(out).split())
    if compact != "".join(out):
        transformations.append("collapsed_duplicate_spaces")
    return compact, transformations


def syllable_like(text: str) -> list[str]:
    units = []
    current = ""
    for char in text:
        if char.isspace():
            if current:
                units.append(current)
                current = ""
            continue
        current += char
        if is_burmese_base(char):
            continue
        if current and len(current) >= 3:
            units.append(current)
            current = ""
    if current:
        units.append(current)
    return units


def is_burmese(char: str) -> bool:
    return BURMESE_START <= char <= BURMESE_END


def is_burmese_base(char: str) -> bool:
    return "\u1000" <= char <= "\u1021"


def write_alignment_text_map(path: Path, occurrences: list[dict[str, Any]], tokenizer_vocab: dict[str, int] | None = None) -> dict[str, Any]:
    payload = build_alignment_text_map(occurrences, tokenizer_vocab)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
