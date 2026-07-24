# API Connector Matrix

Status reflects planning only. Official API availability, pricing, terms, and
regional availability must be rechecked before implementation.

| Tool | Purpose | Official API? | Manual Upload? | Private Media Risk | Cost Risk | Local Possible? | Best Use | Status |
|---|---|---:|---:|---|---|---:|---|---|
| ComfyUI | Local graph execution | Local API yes | Local files | Low if local | GPU/time | Yes | Private local workflows | Stub only |
| Seedance 2.0 / BytePlus ModelArk | High-quality video generation | Yes, through BytePlus ModelArk | Yes | High if cloud | High | No | Wide/medium body motion tests with approved references and approved motion references | Not connected; API credential/spend/region review required; connector disabled |
| Kling | Video generation | Unknown/public availability varies | Yes | High if cloud | Medium/high | No | Action/camera shot tests | Research only |
| Veo | Google video generation | Yes through Google/Vertex availability may vary | Yes | High if cloud | High | No | Premium cinematic tests | Research only |
| OpenAI video | Video generation/research | Unknown/current availability must be verified | Unknown | High if cloud | High | No | Future connector only | Blocked until official docs |
| Wan | Open/local video model family | N/A for local | Local files | Low if local | GPU/time | Yes | Local privacy-first tests | Stub only |
| Runway | Commercial video generation | Yes for some products | Yes | High if cloud | High | No | Polished gen/video tools | Research only |
| Pika | Commercial video generation/effects | Unknown | Yes | High if cloud | Medium/high | No | Stylized short tests | Research only |
| Higgsfield | Workflow AI video platform | Unknown | Yes | High if cloud | High | No | Workflow inspiration | Research only |
| OpenArt | Guided creation workflows | Unknown | Yes | High if cloud | Medium/high | No | UX inspiration | Research only |
| CapCut/DaVinci export | Editing/export handoff | Local/manual | Yes | Medium if cloud sync used | Low/medium | DaVinci yes | Timeline/export integration | Future |
| Microsoft/Azure voice | TTS/voice | Yes | Yes | High for voice data | Medium/high | No | Burmese voice research | Gated |
| VoxCPM2/local voice candidate | Local voice/TTS candidate | N/A local/open | Local files | Low if local | GPU/time | Yes if installable | Private voice tests | Research only |
| NotebookLM/Google voice | Voice/reference workflow research | Product API unknown | Yes | High if cloud | Low/medium | No | Research only, not final voice | Gated |

## Connector Rule

No connector may submit, upload, spend, or download generated output unless an
approval gate exists for the exact request and exact assets.

## Seedance v0.6A.1 Correction

Seedance 2.0 is treated as having an official API path through BytePlus
ModelArk, but Director OS does not connect to it yet. Before implementation:

- review BytePlus ModelArk account, region, pricing, and data-handling terms
- require explicit renderer, reference, upload, and spend approval
- require approved motion-reference video for F01
- keep the connector disabled until the API connector is deliberately built
