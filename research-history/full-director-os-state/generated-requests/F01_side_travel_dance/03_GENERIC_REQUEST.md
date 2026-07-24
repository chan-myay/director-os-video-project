# GENERIC Request Package - F01_side_travel_dance

Generated local review package only. This is not an approval to upload references, spend credits, call cloud tools, render, or generate video.

## Approval State

- Renderer status: template only
- Prompt generation allowed: False
- Human approval required before conversion to final platform prompt.
- Human approval required before any upload, paid generation, or cloud tool use.

## Structured Shot Fields

- shot_id: F01_side_travel_dance
- intent: sustained side-travel dance across bar floor
- song_section_targets: verse1, later_verse, chorus_bridge
- motion.type: side_travel
- motion.direction: lateral
- motion.existing_support: D03, B04, B05
- identity.face_exposure: small_profile_shadowed
- body_wardrobe.proportions: natural_adult
- body_wardrobe.dress: deep_red_one_shoulder
- location.world: dark_teak_bar_winter_window
- camera_lighting.scale: medium_wide_full_body
- camera_lighting.camera: side_tracking

## Creative Locks

- lead performer identity
- natural adult body proportions
- deep red one-shoulder satin Burmese-inspired dress
- dark teak bar
- winter window
- amber/crimson lighting
- Burmese art world
- microphone as symbol only

## Hard Negatives

- no karaoke
- no lounge singer
- no microphone-centered performance
- no fake singing
- no fake lip-sync
- no kung fu
- no martial arts
- no K-pop
- no TikTok
- no exaggerated sexy/model body
- no fake hips/butt/body proportions

## Renderer Mapping Notes

Use the adapter template below as mapping guidance only.
Do not expand into a long final prompt until the user approves this request.

# Generic Renderer Adapter Template

Status: template only. Do not generate prompts or call APIs yet.

This adapter will later convert `RENDERER_FIELDS.yaml` into a generic renderer
request.

Fields to consume:

- `shot_id`
- `intent`
- `song_section`
- `references`
- `motion`
- `identity`
- `body_wardrobe`
- `location`
- `camera_lighting`
- `negative_rules`
- `qc`

Output later:

- concise renderer-neutral request
- selected references list
- reject conditions

No long prose prompt is created in v0.1.

## Draft Request Fields

- Subject: approved adult lead performer performer, identity preserved only from approved references.
- Action: sustained lateral side-travel dance across the bar floor.
- Framing: medium-wide/full-body side tracking, small profile/shadowed face only.
- Mood: mature cinematic blues/jazz tension, elegant controlled movement.
- Environment: dark teak bar, winter window, amber/crimson light, Burmese art world.
- Wardrobe/body: deep red one-shoulder satin dress, natural adult body proportions.
- Reject if face becomes clear close-up, lips appear to sing, body becomes distorted, or staging becomes karaoke/lounge.
