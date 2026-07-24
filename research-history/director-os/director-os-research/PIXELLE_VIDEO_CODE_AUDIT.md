# Pixelle-Video Code Audit

## Audit Status

Director OS attempted to locate and shallow-inspect an official `Pixelle-Video` repository under `local-tools/research-repos/Pixelle-Video/`.

Public search and likely GitHub remote probes did not produce a verifiable anonymous official repository in this environment. The following probes failed with GitHub credential prompts rather than returning public repository metadata:

- `https://github.com/pixelle-ai/Pixelle-Video.git`
- `https://github.com/PixelleAI/Pixelle-Video.git`
- `https://github.com/AIFSH/Pixelle-Video.git`

No Pixelle source code was cloned, executed, copied, or adapted in this build.

## Classification

Because no official source tree was verified locally:

- one-topic quick creation: `ADAPT_PATTERN`
- script generation: `ADAPT_PATTERN`
- script splitting: `ADAPT_PATTERN`
- image planning: `ADAPT_PATTERN`
- frame-by-frame task processing: `ADAPT_PATTERN`
- video composition: `ALREADY_SUPERSEDED_BY_DIRECTOR_OS`
- TTS integration: `ADAPT_PATTERN`
- background music: `ALREADY_SUPERSEDED_BY_DIRECTOR_OS`
- custom-media analysis: `ADAPT_PATTERN`
- image-to-video: `ADAPT_PATTERN`
- digital-human workflow: `ADAPT_PATTERN`
- motion transfer: `ADAPT_PATTERN`
- ComfyUI workflow wrappers: `ADAPT_PATTERN`
- RunningHub workflow wrappers: `INSPIRE_ONLY`
- direct image/video model APIs: `ADAPT_PATTERN`
- model/provider configuration: `ADAPT_PATTERN`
- task history: `ADOPT_PATTERN`
- task cancellation: `ADAPT_PATTERN`
- batch jobs: `ADAPT_PATTERN`
- concurrency limits: `ADAPT_PATTERN`
- structured LLM outputs: `ALREADY_SUPERSEDED_BY_DIRECTOR_OS`
- template system: `ADAPT_PATTERN`
- error handling: `ADAPT_PATTERN`
- retry behaviour: `ADAPT_PATTERN`
- output storage: `ALREADY_SUPERSEDED_BY_DIRECTOR_OS`

## Director OS Adaptation

v2.0 implements the useful patterns without copying Pixelle code:

- atomic capability registry
- interchangeable workflow providers
- one-prompt pipeline UX
- structured task history
- safe local concurrency by iteration limits
- direct local tool routing
- frame/animatic assembly through existing FFmpeg pipeline
- custom media evaluation entry point
- motion/lip-sync abstraction remains behind approval gates

## License Notes

No Pixelle code was adopted, so no Apache-2.0 code notice is required for copied files. If an official repository is later provided and code is copied, Director OS must preserve Apache-2.0 notices and separately review model/provider licenses.
