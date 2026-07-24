# GitHub Foundation Audit

No repositories were cloned in v0.3. Do not clone large model weights. If a
repository must be inspected later, use shallow clones under:

`local-tools/research-repos/`

Ask before cloning when the repository is large, includes model weights, or has
unclear licensing.

## OpenMontage

- Status: not cloned.
- Potential value: montage/story assembly inspiration.
- Audit needed: license, code size, dependencies, model weights, data policy.
- Product decision: inspiration only until reviewed.

## ViMax

- Status: not cloned.
- Potential value: UNKNOWN until exact repository is identified.
- Audit needed: license, repo purpose, media pipeline, model weights.
- Product decision: do not adopt blindly.

## FireRed-OpenStoryline

- Status: not cloned.
- Potential value: story/scene/shot planning ideas.
- Audit needed: license, architecture, dependency weight, model requirements.
- Product decision: possible planning-layer inspiration.

## ComfyUI

- Status: not cloned in v0.3.
- Potential value: local node workflow backend and reproducible graphs.
- Audit needed: deployment model, extension security, workflow API, license,
  custom node risk.
- Product decision: strong candidate as optional local renderer backend, not the
  product foundation.

## ComfyUI-Manager

- Status: not cloned.
- Potential value: extension discovery and install management.
- Audit needed: security, supply-chain risk, extension vetting, public SaaS
  suitability.
- Product decision: risky for hosted SaaS without strict sandboxing.

## AI Storyboard Generator

- Status: not cloned.
- Potential value: storyboard UI ideas if exact project is identified.
- Audit needed: license, generation dependencies, export format.
- Product decision: inspiration only.

## SoeMind Forge

- Status: not cloned.
- Potential value: optional local inspiration.
- Audit needed: license, install footprint, product fit.
- Product decision: reference only, not main foundation.
