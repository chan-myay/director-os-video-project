# Burmese-First Strategy

Director OS should make Burmese music-video production a primary workflow, not a
localized version of a generic English video tool.

## Lyrics

- Store Burmese lyrics as a first-class project file.
- Support line timing, section labels, emotional tone, and movement intensity.
- Keep original Burmese text separate from English explanations.

## Zawgyi / Unicode Handling

- Detect and normalize Burmese text encoding.
- Preserve original source text for evidence.
- Store normalized Unicode for search, captions, and prompts.
- Flag uncertain conversion for human review.

## Pronunciation Rewriting Layer

- Add a pronunciation planning layer for voice/lip-sync tools.
- Support romanization, phoneme notes, and singer-specific phrasing.
- Do not treat generated singing as final lip-sync.

## Captions

- Support Burmese captions.
- Support bilingual captions when needed.
- Keep caption timing editable.

## TTS / Voice-Clone Adapter Layer

- Future adapters may include Microsoft/Azure voice, local candidates such as
  VoxCPM2, or manual vocal workflows.
- Voice cloning requires explicit consent.
- Burmese pronunciation quality must be tested before public claims.

## Cultural Reference Library

- Store Burmese clothing, craft, stage, architecture, typography, gesture, and
  music-video references as tagged metadata.
- Do not scrape or rehost copyrighted stills.
- Store URLs, rights notes, and user-owned uploads.

## Avoid Drift

Hard rejects:

- Generic Asian substitution.
- Chinese/Korean/Japanese visual drift unless explicitly part of the project.
- K-pop dance vocabulary when the song needs Burmese cinematic bar tension.
- Karaoke/lounge defaults.

## Product Principle

Burmese visual and cultural details are locked fields in the director bible and
shot pack, not decorative adjectives.
