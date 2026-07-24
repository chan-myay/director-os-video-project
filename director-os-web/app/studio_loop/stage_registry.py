from __future__ import annotations

from app.studio_loop.schemas import STAGES


def production_graph() -> list[dict]:
    dependencies = {
        "project_understanding": [],
        "research": ["project_understanding"],
        "director_plan": ["project_understanding", "research"],
        "song_music": ["project_understanding"],
        "burmese_language": ["song_music"],
        "caption_sync": ["burmese_language", "song_music"],
        "storyboard_previs": ["director_plan"],
        "image_generation": ["storyboard_previs"],
        "video_generation": ["image_generation"],
        "voice": ["burmese_language"],
        "lip_sync": ["caption_sync", "voice"],
        "editing": ["storyboard_previs", "caption_sync"],
        "assembly": ["editing"],
        "qc": ["assembly"],
        "repair": ["qc"],
    }
    return [{"task": task, "dependencies": deps} for task, deps in dependencies.items()]


def stage_list() -> list[str]:
    return list(STAGES)
