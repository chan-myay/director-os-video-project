# Burmese Technology Audit

## Implemented In v1.0

- Conservative Zawgyi/Unicode detection.
- Original lyric preservation.
- Unicode NFC normalization.
- Lyric-line segmentation.
- Simple syllable/phrase segmentation.
- Pronunciation-helper field.
- Caption-safe line splitting.
- Local font detection.
- Timeline export:
  - `director-os/burmese-language/BURMESE_LYRIC_TIMELINE.json`
  - `director-os/burmese-language/BURMESE_LYRIC_TIMELINE.md`

## Important Limits

- Full Zawgyi-to-Unicode conversion is not claimed operational yet.
- The current converter is conservative passthrough until an audited Myanmar Tools adapter is integrated.
- Burmese TTS is not operational until a provider produces a real benchmark WAV.
- Voice cloning remains disabled without explicit consent and approved voice references.

## Required Next Audit

- Myanmar Tools or equivalent maintained Zawgyi/Unicode converter.
- Burmese segmentation/tokenization libraries.
- Burmese ASR/TTS candidates.
- Locally available Burmese fonts and rendering behavior in the web app.

## Decision

ADAPT Burmese text tooling into Director OS, but keep conversion uncertainty visible and manual corrections authoritative.
