# Video Generation Locality Audit

## Conclusion

Final cinematic video generation is not marked operational locally in v1.0.

The current Mac can run deterministic media assembly and may be able to run smaller Apple-Silicon image or local LLM workloads after explicit approval, but no local video model was installed or benchmarked during this build.

## Candidate Classes

| Candidate | Local classification | Decision | Reason |
|---|---|---|---|
| Wan variants | local_experimental | DEFER | Needs model/runtime/license and memory review before any download. |
| LTX-Video | local_experimental/private_remote_option | DEFER | Public paper reports high performance on H100-class hardware; Apple Silicon feasibility must be proven separately. |
| FramePack | local_experimental | DEFER | Needs source/security review. |
| Wan2GP | local_experimental | DEFER | Needs source/security review and no untrusted custom-node execution. |
| HunyuanVideo | private_remote_option | DEFER | Likely too heavy locally without careful benchmark. |
| CogVideoX | local_but_slow/private_remote_option | DEFER | Needs exact model and Apple Silicon runtime benchmark. |
| InfiniteTalk | local_after_install/private_remote_option | DEFER | Lip-sync/performance tool, not general movement generator; no model installed. |

## Practical Path

Keep these local:

- project memory
- research
- Burmese language
- captions
- storyboard structure
- composite previs
- animatic
- edit/QC

Use remote execution only after explicit approval for exact files, spend, endpoint and retention policy.
