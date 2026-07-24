# Project Handoff — Director OS / The Bar Remembers Her

## Executive status

Director OS is a local-first creative production workspace for a full-song
Burmese music video. The useful project evidence has been preserved. The current
priority is not more architecture or another alignment experiment; it is a
finished, emotionally coherent visual edit built from existing material plus a
small number of targeted replacement shots.

The creative concept is **The Bar Remembers Her**. The lead performer is a
consenting adult over 40. The approved direction is a mature singing performance
in a dark-teak Finnish bar, expanded by Finnish winter exteriors and restrained
Burmese cultural imagery.

The lead performer is not required to dance. Her performance should prioritize
singing, emotional presence, natural breathing, small weight shifts, restrained
head turns, and subtle shoulder response. The wider film is not limited to
static bar coverage: tasteful adult background movement or dance, band activity,
memory imagery, exterior life, and visual rhythm are available when they serve
the song. Body emphasis, unnecessary rear views, and movement resembling martial
arts or social-media choreography remain unacceptable.

## Source-of-truth assets

The workstation contains the complete private and heavyweight evidence. GitHub
contains code, metadata, prompts, direction, and recovery documentation only.

| ID | Role | Classification |
|---|---|---|
| A1 | front identity reference | approved source; private |
| A2 | three-quarter identity reference | approved source; private |
| B | full-body and deep-red one-shoulder wardrobe reference | approved source; private |
| C | dark-teak Finnish bar and winter-window reference | approved reference |
| E | Burmese art, architecture, and material-world reference | approved reference |
| Song | canonical full-length master | approved source; local only |
| Lyrics | corrected Unicode Burmese lyrics | approved source; local only |
| Storyboard composites | layout and sequence evidence | composite; never label as AI-generated frames |
| Imported/generated media | candidate images and clips | generated image or generated video |
| Failure memory | rejected and restricted material | preserved; never silently reactivate |

Neutral filenames in this repository use `PERFORMER`. A workstation created
before this privacy cleanup may still use an older personal label in local asset
filenames. Map those files to A1, A2, and B; do not duplicate or regenerate the
underlying references.

## Creative lock

Preserve:

- Same lead performer and approved A1/A2 identity.
- Same realistic body proportions and approved B wardrobe.
- Same dark-teak Finnish bar, winter window, amber/crimson practical light, and
  cold exterior contrast.
- Mature emotional restraint and professional cinematic camera movement.
- Burmese cultural material identity without turning the scene into a generic
  pan-Asian environment.
- Occasional exterior bar views, winter nature, Burmese architecture/art,
  restrained adult band coverage, and a sparse mature adult audience.
- Creative expansion beyond the bar: streets, snow, landscape, architectural
  details, symbolic objects, memory fragments, transitions between Finland and
  Burmese cultural space, and other clean cinematic ideas supported by the song.
- Tasteful adult background dance or social movement when emotionally motivated;
  it must never pressure the lead performer into choreography or turn the film
  into a club, karaoke, or dance-video concept.

Reject:

- Forced choreography for the lead performer, exaggerated swaying, hip-led
  motion, or rear/body emphasis.
- Karaoke, lounge-singer, or microphone-centred staging.
- Kung fu, martial arts, K-pop, TikTok, or music-video dance vocabulary.
- Identity drift, generic replacement, artificial anatomy, glamour
  de-aging, or youth-coded styling.
- Children or child-containing reference material.
- Incorrect Burmese captions or unverified lyric timing.

## Current deliverables

The local rescue-studio directory contains:

- `STORYBOARD_ANIMATIC_CLEAN.mp4`: full-song H.264/AAC animatic, no captions or
  technical overlays.
- `STORYBOARD_ANIMATIC_REVIEW.mp4`: review copy with shot and camera information.
- `STORYBOARD_CONTACT_SHEET.png`.
- `STORYBOARD.json`: 24-shot sequence metadata.
- `PROJECT_SUMMARY.json`: cached project input summary.
- `EXISTING_VIDEO_AUDIT.json`: existing clip inventory and classifications.
- `BUILD_LOG.txt`.
- `prompts/SHOT_001` through `prompts/SHOT_024`.
- `prompts/ALL_SHOTS.md` and `prompts/SHOT_INDEX.json`.
- managed imports and lightweight thumbnails.

The clean animatic is explicitly a **raw storyboard animation, not a final
generated video**.

## Existing media policy

Do not discard existing work.

- Retain acceptable environment and object clips from the earlier production.
- Reuse performer clips only when the face, body, framing, and movement pass the
  current restrictions.
- Mouth-safe holds, profiles, and restrained expressions can remain before
  reliable lip-sync.
- Earlier dance-led performer material remains excluded unless it independently
  passes the current mature-performance review. Background social movement or
  dance may be used selectively when it strengthens the world and the song.
- Travel material that does not belong to the bar/winter/Burmese-world concept
  remains excluded.
- Imported replacements must keep their source files untouched. Managed copies
  can be assigned to shots, compared, selected, and used during rebuild.

The revised reuse/generation decision is documented in:

- `creative-direction/REARRANGED_EDIT_AND_GENERATION_MATRIX.md`
- `creative-direction/SURGICAL_REPLACEMENT_MAP.md`
- `creative-direction/DANCE_EXCLUSION_LOCK.json`

## Minimum new generation

The first generation round should stay small:

1. Mature three-quarter emotional performer reveal in the established bar.
2. Restrained adult band insert that supports the performer without becoming a
   concert scene.
3. Sparse mature adult audience/reaction insert.

Additional portrait, winter-window, Burmese-world, or ending replacements are
conditional and should be generated only when existing footage fails review.
Use `creative-direction/GEMINI_FIRST_GENERATION.md` and
`creative-direction/G02_G04_SUPPORTING_WORLD_PROMPTS.md`.

Third-party generation is a manual export/import workflow unless explicit API
access and provider approval are added later. Never claim an automatic provider
render that did not occur.

## Lip-sync and Burmese caption status

Lip-sync work is preserved, not lost, but it is not currently an approval gate
for the visual production.

- Exact Burmese audio-to-lyric timing is only partially verified. The v4
  artifact marks 9 occurrences ready and 12 blocked. The early anchor is
  human-verified; middle and late replacement anchors passed media validation
  but still require timing/semantic confirmation. Real review invalidated two
  prior occurrence decisions, and those invalidations must be preserved.
- Lip-sync is disabled by default until reliable timing and an approved source
  clip exist.
- Gemini/Flow generation must not be represented as accurate Burmese lip-sync.
- Generate visually clean, mouth-safe footage first.
- The clean animatic contains no lyric captions.
- Optional captions must use verified-only timing; uncertain lines stay hidden.
- Audio Truth code, evidence, analysis, and prior runs remain available under
  Advanced for later forensic review.
- Do not launch another Audio Truth version merely to unblock storyboarding.

The repository preserves local, manual, and RunPod InfiniteTalk provider
adapters, eligibility checks, audio segmentation, QC, and planning code. Their
presence is capability preservation, not proof of an approved lip-sync output.

Lip-sync can resume only after all of the following:

1. A visual shot is accepted.
2. The performer face is sufficiently stable or has passed face correction.
3. The relevant vocal segment boundaries are verified.
4. The chosen provider is configured and explicitly approved.
5. A short test passes identity, mouth motion, timing, anatomy, and artifact QC.
6. The result is reviewed before insertion into the full edit.

The complete v2/v3/v4 evidence, ASR outputs, anchors, segments, failures, and
package/model records is under `research-history/audio-truth/`. See
`RESEARCH_INDEX.md`; do not infer alignment status from the UI alone.

## Face correction

Face correction follows visual acceptance; it should not be run on every
generated candidate.

Approved retained workflows:

- HiFiFace 256.
- UniFace 256.

The local workstation also preserves trained performer models under
`face-correction/`. Model binaries are intentionally excluded from GitHub.
Evaluate both approved workflows on the accepted source clip, select the cleaner
identity match with fewer temporal artifacts, and preserve the untouched source.

## Rescue Studio behavior

The FastAPI application lives in `director-os-web/`.

- `/` redirects directly to `/create`.
- GET requests use cached summaries and do not load models, analyze audio, or run
  the Studio Loop.
- The primary page shows project inputs, one optional idea field, create/import
  actions, concept, storyboard, animatic, prompt package, and imported results.
- Technical systems remain under Advanced.
- Create, import, refinement, and rebuild operations use background jobs.
- Navigation is not covered by a blocking spinner.
- Imported JPG, PNG, MP4, and MOV files are probed, assigned by filename when
  possible, and rejected if corrupted.
- Supported examples include `SHOT_001.png`, `SHOT_001_v2.png`,
  `SHOT_006.mp4`, and `F07_final.mp4`.

Important routes and code:

- UI: `director-os-web/app/templates/rescue_create.html`
- Browser behavior: `director-os-web/app/static/rescue.js`
- Styles: `director-os-web/app/static/rescue.css`
- Rescue orchestration: `director-os-web/app/services/rescue_studio_service.py`
- Application routes: `director-os-web/app/main.py`
- Advanced Audio Truth archive:
  `director-os-web/app/templates/advanced_audio_archive.html`

## One-sentence refinement

Refinement is surgical. Interpret a sentence, identify affected shots, update
only those shots, and rebuild in the background. Valid examples:

- Make the chorus stronger.
- Make it darker and more emotional.
- Use fewer close-ups.
- Keep the performer on the right side.
- Show more of the winter window.
- Remove background people.
- Make movement natural, not choreographed.
- Use the new Gemini clips.
- Replace shot 7.
- Make the ending more powerful.

Never silently overwrite source media or globally rewrite unaffected shots.

## Recommended continuation sequence

1. Confirm the canonical song and private A1/A2/B/C/E references resolve locally.
2. Start the local service and open `/create`.
3. Review the current storyboard and clean full-song animatic.
4. Audit existing candidates against the mature-performance creative lock:
   restrained lead performance, with broader cinematic freedom around her.
5. Generate only the three first-round replacements.
6. Import results using clear shot-oriented filenames.
7. Select the best variants and rebuild the clean animatic.
8. Refine the sequence for emotion, winter/bar geography, Burmese material
   identity, chorus energy, and ending power.
9. Face-correct accepted performer clips using the approved comparison workflow.
10. Verify caption timing separately.
11. Run a short lip-sync proof only after timing, provider, source clip, and QC
    gates are satisfied.
12. Rebuild and review the full-song master without cutoff.

For a private GPU host, continue with `GPU_SERVER_RUNBOOK.md`. It separates
recoverable research from local-only binaries and prevents expensive runs from
overwriting human review or historical evidence.

## Acceptance checklist

- `/create` is visible quickly and its controls are immediately usable.
- Storyboard grid, sequence, and frame views work.
- The clean animatic plays and seeks through the full song.
- All 24 prompt packages are accessible.
- Import works without manifests or manual JSON editing.
- Existing acceptable clips are represented in the edit.
- Forced or unsuitable lead-performer dance shots remain excluded; any background
  movement used is intentional, mature, and song-driven.
- Rebuild runs in the background and navigation remains responsive.
- No unverified Burmese text appears in the clean output.
- Lip-sync remains disabled unless every stated gate passes.
- The final handoff clearly distinguishes approved sources, references,
  composites, generated images, generated videos, rejected assets, and
  restricted assets.
