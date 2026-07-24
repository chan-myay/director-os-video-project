from __future__ import annotations

from typing import Any


STAGES = [
    "project_archaeology",
    "music_analysis",
    "burmese_language_analysis",
    "public_research",
    "concept_development",
    "concept_selection",
    "character_and_performance",
    "environment_and_production_design",
    "composition_and_blocking",
    "lighting_and_cinematography",
    "movement_direction",
    "storyboard_generation",
    "caption_and_voice_plan",
    "edit_and_animatic",
    "renderer_strategy",
    "production_preparation",
    "ready_for_review",
]


STAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["stage", "summary", "confidence", "sources", "artifacts", "blockers", "data"],
    "properties": {
        "stage": {"type": "string"},
        "summary": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "confidence"],
                "properties": {
                    "source": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
        "artifacts": {"type": "array", "items": {"type": "string"}},
        "blockers": {"type": "array", "items": {"type": "string"}},
        "data": {"type": "object"},
    },
}


DIRECTOR_RUN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["project_understanding", "concepts", "selected_concept", "storyboard", "renderer_strategy", "questions"],
    "properties": {
        "project_understanding": {"type": "object"},
        "concepts": {"type": "array", "items": {"type": "object"}},
        "selected_concept": {"type": "object"},
        "storyboard": {"type": "array", "items": {"type": "object"}},
        "renderer_strategy": {"type": "array", "items": {"type": "object"}},
        "questions": {"type": "array", "items": {"type": "string"}, "maxItems": 3},
    },
}
