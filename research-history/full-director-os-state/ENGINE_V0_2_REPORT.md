# Engine v0.2 Report

## What Compiler Created

- Added local Python compiler: `tools/compile_shot_pack.py`
- Added generated request package folder:
  `generated-requests/F01_side_travel_dance/`
- The compiler reads:
  - F01 `RENDERER_FIELDS.yaml`
  - F01 rule markdown files
  - global project rules
  - creative lock
  - asset path registry
  - renderer adapter templates
- The compiler writes local markdown review packages only.

## F01 Human Review Status

F01 is ready for human review as a controlled request package.

It is not approved for generation. It is not approved for upload. It is not a
final renderer prompt.

## Still Missing Before Real Generation

- User selection of renderer/tool.
- User approval of exact reference files to upload/use.
- Privacy approval for any upload of approved lead performer identity references.
- Final renderer-specific request approval.
- Spend/credit/time limit.
- Confirmation that no child-containing, rejected, or broad private source
  folders are included.
- Normal-speed QC criteria acceptance.

## Most Suitable Renderer For F01

Most suitable later candidate: `Seedance`.

Reason: F01 is a wide/medium body-and-motion shot, not a close identity shot and
not a lip-sync shot. The Seedance adapter is already scoped for wide/medium body
dance footage, where the main need is controlled lateral movement, correct
wardrobe/body proportions, and environment consistency. This recommendation
does not approve using Seedance or uploading references.

Secondary option: `Kling`, if the user wants a platform more focused on action
field mapping and manual negative controls.

## User Must Approve Next

- Review `generated-requests/F01_side_travel_dance/00_APPROVAL_GATE.md`.
- Review `03_GENERIC_REQUEST.md` before any platform-specific version.
- Choose whether F01 remains the first future test.
- Choose renderer only after comparing request files.
- Approve exact references, final request, and spend limit before any future
  generation.
