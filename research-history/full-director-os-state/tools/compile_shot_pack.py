#!/usr/bin/env python3
"""Compile one Director OS shot pack into local renderer request packages.

This script is intentionally local-only. It reads markdown/YAML control files
and writes review documents. It does not call APIs, upload media, render, or
generate video.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
from typing import Any


ENGINE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SHOT_ID = "F01_side_travel_dance"

GENERATED_WARNING = (
    "Generated local review package only. This is not an approval to upload "
    "references, spend credits, call cloud tools, render, or generate video."
)

HARD_NEGATIVES = [
    "no karaoke",
    "no lounge singer",
    "no microphone-centered performance",
    "no fake singing",
    "no fake lip-sync",
    "no kung fu",
    "no martial arts",
    "no K-pop",
    "no TikTok",
    "no exaggerated sexy/model body",
    "no fake hips/butt/body proportions",
]

CREATIVE_LOCKS = [
    "lead performer identity",
    "natural adult body proportions",
    "deep red one-shoulder satin Burmese-inspired dress",
    "dark teak bar",
    "winter window",
    "amber/crimson lighting",
    "Burmese art world",
    "microphone as symbol only",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_scalar(value: str) -> Any:
    value = value.strip()
    if value in {"true", "false"}:
        return value == "true"
    if value in {"[]", "{}"}:
        return ast.literal_eval(value)
    if value.startswith("[") and value.endswith("]"):
        return ast.literal_eval(value)
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return ast.literal_eval(value)
    return value


def parse_simple_yaml(path: Path) -> dict[str, Any]:
    """Parse the simple YAML subset used by the current Director OS files."""
    lines = read_text(path).splitlines()
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for index, raw_line in enumerate(lines):
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue

        indent = len(raw_line) - len(raw_line.lstrip(" "))
        line = raw_line.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            item = parse_scalar(line[2:])
            if not isinstance(parent, list):
                raise ValueError(f"Unexpected list item in {path}: {raw_line}")
            parent.append(item)
            continue

        if ":" not in line:
            raise ValueError(f"Unsupported YAML line in {path}: {raw_line}")

        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()

        if raw_value == "":
            container = {}
            for lookahead in lines[index + 1 :]:
                if not lookahead.strip() or lookahead.lstrip().startswith("#"):
                    continue
                next_indent = len(lookahead) - len(lookahead.lstrip(" "))
                if next_indent > indent and lookahead.strip().startswith("- "):
                    container = []
                break
            if isinstance(parent, dict):
                parent[key] = container
            else:
                raise ValueError(f"Unexpected mapping in list in {path}: {raw_line}")
            stack.append((indent, container))
            continue

        value = parse_scalar(raw_value)
        if isinstance(parent, dict):
            parent[key] = value
        else:
            raise ValueError(f"Unexpected key/value in list in {path}: {raw_line}")

        if isinstance(value, list):
            stack.append((indent, value))

    return root


def bullet_list(items: list[Any]) -> str:
    if not items:
        return "- UNKNOWN\n"
    return "\n".join(f"- {item}" for item in items) + "\n"


def field_line(label: str, value: Any) -> str:
    if isinstance(value, list):
        return f"- {label}: {', '.join(str(item) for item in value) if value else 'UNKNOWN'}"
    if isinstance(value, dict):
        inner = ", ".join(f"{k}={v}" for k, v in value.items())
        return f"- {label}: {inner or 'UNKNOWN'}"
    return f"- {label}: {value if value not in (None, '') else 'UNKNOWN'}"


def markdown_block(title: str, lines: list[str]) -> str:
    return f"## {title}\n\n" + "\n".join(lines).rstrip() + "\n"


def load_context(shot_id: str) -> dict[str, Any]:
    shot_dir = ENGINE_ROOT / "shot-packs" / shot_id
    adapter_root = ENGINE_ROOT / "render-adapters"
    return {
        "shot_id": shot_id,
        "shot_dir": shot_dir,
        "fields": parse_simple_yaml(shot_dir / "RENDERER_FIELDS.yaml"),
        "project_rules": parse_simple_yaml(ENGINE_ROOT / "config" / "project_rules.yaml"),
        "creative_lock": parse_simple_yaml(ENGINE_ROOT / "config" / "creative_lock.yaml"),
        "asset_paths": parse_simple_yaml(ENGINE_ROOT / "config" / "asset_paths.yaml"),
        "renderers": parse_simple_yaml(ENGINE_ROOT / "config" / "renderers.yaml"),
        "shot_intent": read_text(shot_dir / "SHOT_INTENT.md"),
        "motion_reference": read_text(shot_dir / "MOTION_REFERENCE.md"),
        "identity_rules": read_text(shot_dir / "IDENTITY_RULES.md"),
        "body_wardrobe_rules": read_text(shot_dir / "BODY_WARDROBE_RULES.md"),
        "location_rules": read_text(shot_dir / "LOCATION_RULES.md"),
        "negative_rules": read_text(shot_dir / "NEGATIVE_RULES.md"),
        "templates": {
            name: read_text(adapter_root / name / "PROMPT_TEMPLATE.md")
            for name in ["generic", "kling", "seedance", "wan", "veo"]
        },
    }


def references_section(fields: dict[str, Any], asset_paths: dict[str, Any]) -> str:
    refs = fields.get("references", {})
    approved = asset_paths.get("approved_references", {})
    forbidden = asset_paths.get("forbidden_references", {})

    lines = [
        field_line("Identity references requested by shot pack", refs.get("identity")),
        field_line("Wardrobe/body references requested by shot pack", refs.get("wardrobe_body")),
        field_line("Location references requested by shot pack", refs.get("location")),
        "",
        "Approved registry cross-check:",
        field_line("lead performer_face_front", approved.get("lead performer_face_front")),
        field_line("lead performer_face_threequarter", approved.get("lead performer_face_threequarter")),
        field_line("wardrobe_body", approved.get("wardrobe_body")),
        field_line("bar_stage", approved.get("bar_stage")),
        field_line("burmese_art", approved.get("burmese_art")),
        "",
        "Privacy and upload lock:",
        "- Do not upload child-containing sources.",
        "- Do not upload rejected identity sheets.",
        "- Do not upload broad private lead performer source folders.",
        "- Upload/use only approved references after explicit user approval.",
        "",
        "Forbidden references:",
        field_line("rejected_three_angle_sheet", forbidden.get("rejected_three_angle_sheet")),
        field_line("simswap_pilot", forbidden.get("simswap_pilot")),
        field_line("child_sources", forbidden.get("child_sources")),
    ]
    return "\n".join(lines) + "\n"


def renderer_request(renderer: str, context: dict[str, Any]) -> str:
    fields = context["fields"]
    template = context["templates"][renderer]
    renderer_config = context["renderers"].get("renderers", {}).get(renderer, {})
    motion = fields.get("motion", {})
    identity = fields.get("identity", {})
    body = fields.get("body_wardrobe", {})
    location = fields.get("location", {})
    camera = fields.get("camera_lighting", {})

    title = renderer.upper() if renderer != "generic" else "GENERIC"
    sections = [
        f"# {title} Request Package - {fields.get('shot_id', context['shot_id'])}\n",
        GENERATED_WARNING + "\n",
        markdown_block(
            "Approval State",
            [
                field_line("Renderer status", renderer_config.get("status")),
                field_line("Prompt generation allowed", renderer_config.get("prompt_generation_allowed")),
                "- Human approval required before conversion to final platform prompt.",
                "- Human approval required before any upload, paid generation, or cloud tool use.",
            ],
        ),
        markdown_block(
            "Structured Shot Fields",
            [
                field_line("shot_id", fields.get("shot_id")),
                field_line("intent", fields.get("intent")),
                field_line("song_section_targets", fields.get("song_section_targets")),
                field_line("motion.type", motion.get("type")),
                field_line("motion.direction", motion.get("direction")),
                field_line("motion.existing_support", motion.get("existing_support")),
                field_line("identity.face_exposure", identity.get("face_exposure")),
                field_line("body_wardrobe.proportions", body.get("proportions")),
                field_line("body_wardrobe.dress", body.get("dress")),
                field_line("location.world", location.get("world")),
                field_line("camera_lighting.scale", camera.get("scale")),
                field_line("camera_lighting.camera", camera.get("camera")),
            ],
        ),
        markdown_block("Creative Locks", [bullet_list(CREATIVE_LOCKS).rstrip()]),
        markdown_block("Hard Negatives", [bullet_list(HARD_NEGATIVES).rstrip()]),
        markdown_block(
            "Renderer Mapping Notes",
            [
                "Use the adapter template below as mapping guidance only.",
                "Do not expand into a long final prompt until the user approves this request.",
                "",
                template.rstrip(),
            ],
        ),
        markdown_block(
            "Draft Request Fields",
            [
                "- Subject: approved adult lead performer performer, identity preserved only from approved references.",
                "- Action: sustained lateral side-travel dance across the bar floor.",
                "- Framing: medium-wide/full-body side tracking, small profile/shadowed face only.",
                "- Mood: mature cinematic blues/jazz tension, elegant controlled movement.",
                "- Environment: dark teak bar, winter window, amber/crimson light, Burmese art world.",
                "- Wardrobe/body: deep red one-shoulder satin dress, natural adult body proportions.",
                "- Reject if face becomes clear close-up, lips appear to sing, body becomes distorted, or staging becomes karaoke/lounge.",
            ],
        ),
    ]
    return "\n".join(sections)


def approval_gate(context: dict[str, Any]) -> str:
    fields = context["fields"]
    return f"""# Approval Gate - {fields.get('shot_id', context['shot_id'])}

{GENERATED_WARNING}

## Current State

- Shot pack compiled for human review.
- No renderer has been approved.
- No references are approved for upload by this package.
- No paid/cloud generation is approved.
- No final platform prompt has been approved.

## Required User Approvals Before Any Real Generation

- Renderer/tool choice.
- Exact reference files allowed for upload.
- Confirmation that no child-containing or rejected sources are included.
- Final renderer-specific request text.
- Spend/credit/time limit.
- Privacy risk acceptance for uploading approved lead performer identity references, if a cloud renderer is chosen.

## Locked Creative Requirements

{bullet_list(CREATIVE_LOCKS)}
## Hard Stops

{bullet_list(HARD_NEGATIVES)}
"""


def motion_requirements(context: dict[str, Any]) -> str:
    fields = context["fields"]
    motion = fields.get("motion", {})
    return f"""# Motion Reference Requirements - {fields.get('shot_id', context['shot_id'])}

{GENERATED_WARNING}

## Required Motion

- Type: {motion.get('type', 'UNKNOWN')}
- Direction: {motion.get('direction', 'UNKNOWN')}
- Existing support clips/labels: {', '.join(motion.get('existing_support', [])) or 'UNKNOWN'}
- Camera relation: side tracking
- Movement: rhythmic lateral travel, controlled profile turn, continued travel
- Energy: mature, elegant, cinematic blues/jazz, Black-Swan tension

## Source Rule

- Use approved project evidence only.
- Do not use child-containing source videos.
- Do not use rejected identity sheets.
- Do not use broad private lead performer source folders.
- If a renderer needs an uploaded motion clip later, user must approve the exact file first.

## Original F01 Motion Notes

{context['motion_reference'].rstrip()}
"""


def negative_lock(context: dict[str, Any]) -> str:
    fields = context["fields"]
    return f"""# Negative Lock - {fields.get('shot_id', context['shot_id'])}

{GENERATED_WARNING}

## Global Hard Negatives

{bullet_list(HARD_NEGATIVES)}
## Shot-Specific Negative Rules

{context['negative_rules'].rstrip()}
"""


def qc_scorecard(context: dict[str, Any]) -> str:
    fields = context["fields"]
    return f"""# QC Scorecard - {fields.get('shot_id', context['shot_id'])}

{GENERATED_WARNING}

Score each item after any future test generation. A failing critical item rejects
the shot.

| Item | Pass/Fail/UNKNOWN | Notes |
|---|---|---|
| Lead performer identity remains from approved references only | UNKNOWN | |
| Face stays small/profile/shadowed/not readable | UNKNOWN | |
| Natural adult body proportions | UNKNOWN | |
| Deep red one-shoulder dress preserved | UNKNOWN | |
| Dark teak bar / winter window / amber-crimson world preserved | UNKNOWN | |
| Burmese art world not contradicted | UNKNOWN | |
| Sustained side-travel motion is clear | UNKNOWN | |
| Movement is mature blues/jazz/Black-Swan tension | UNKNOWN | |
| No karaoke/lounge/microphone-centered staging | UNKNOWN | |
| No fake lip-sync or fake singing | UNKNOWN | |
| No kung fu/martial arts/K-pop/TikTok movement | UNKNOWN | |
| Hands, legs, feet, dress physics are clean | UNKNOWN | |
| Normal-speed review completed | UNKNOWN | |
"""


def decision_log(context: dict[str, Any]) -> str:
    fields = context["fields"]
    return f"""# Decision Log - {fields.get('shot_id', context['shot_id'])}

## Compiler Decision

- Created renderer request package for review only.
- No generation approved.
- No upload approved.
- No renderer selected as final.

## Recommended First Review

Review `03_GENERIC_REQUEST.md` first, then compare platform-specific mapping in:

- `04_KLING_REQUEST.md`
- `05_SEEDANCE_REQUEST.md`
- `06_WAN_REQUEST.md`
- `07_VEO_REQUEST.md`

## Open Decisions

- Select renderer.
- Approve exact references for upload/use.
- Approve exact motion source if any renderer requires one.
- Approve final request text.
- Approve spend/credit limit.
"""


def compile_shot_pack(shot_id: str) -> list[Path]:
    context = load_context(shot_id)
    fields = context["fields"]
    output_dir = ENGINE_ROOT / "generated-requests" / shot_id
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {
        "00_APPROVAL_GATE.md": approval_gate(context),
        "01_SOURCE_ASSET_LIST.md": (
            f"# Source Asset List - {fields.get('shot_id', shot_id)}\n\n"
            f"{GENERATED_WARNING}\n\n"
            + references_section(fields, context["asset_paths"])
        ),
        "02_MOTION_REFERENCE_REQUIREMENTS.md": motion_requirements(context),
        "03_GENERIC_REQUEST.md": renderer_request("generic", context),
        "04_KLING_REQUEST.md": renderer_request("kling", context),
        "05_SEEDANCE_REQUEST.md": renderer_request("seedance", context),
        "06_WAN_REQUEST.md": renderer_request("wan", context),
        "07_VEO_REQUEST.md": renderer_request("veo", context),
        "08_NEGATIVE_LOCK.md": negative_lock(context),
        "09_QC_SCORECARD.md": qc_scorecard(context),
        "10_DECISION_LOG.md": decision_log(context),
    }

    written: list[Path] = []
    for name, content in outputs.items():
        path = output_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "shot_id",
        nargs="?",
        default=DEFAULT_SHOT_ID,
        help=f"Shot pack folder name. Default: {DEFAULT_SHOT_ID}",
    )
    args = parser.parse_args()

    written = compile_shot_pack(args.shot_id)
    print(f"Compiled {args.shot_id} into {written[0].parent}")
    for path in written:
        print(path.relative_to(ENGINE_ROOT.parent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
