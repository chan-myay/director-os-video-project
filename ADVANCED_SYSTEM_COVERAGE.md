# Legacy Advanced System Coverage

The old Advanced system is preserved as engineering evidence and continuation
material. The fast `/create` page is the primary product, but it does not erase
the work behind Advanced.

## Coverage matrix

| Advanced area | Implementation | Historical evidence | Current truth |
|---|---|---|---|
| Audio Truth | `director-os-web/app/audio_truth/`, `app/audio/`, run scripts | `research-history/audio-truth/`, `research-history/full-director-os-state/captions/`, `listening-sync/`, `state/` | v4 is partial: 9 ready, 12 blocked; one verified anchor |
| Canonical Burmese lyrics | `app/burmese/`, lyric services | normalized lyrics, Unicode/Zawgyi audits, source hashes, pronunciation and meaning records | corrected Unicode is canonical; stale Zawgyi retained only as provenance |
| Caption alignment | caption, listening-sync, offset and calibration services | all caption versions, final-timing attempts, ASR windows, anchor and timing evaluations | clean output hides unverified captions |
| Music analysis/brain | music analysis, brain sync, production workspace services | production brain/state, analyses, plans, timing authority, evaluations | usable for visual structure; not proof of exact lyric timing |
| Lip-sync planning | `app/lipsync/` and lip-sync services/templates | eligibility maps, segment metadata, lyrics, pronunciation, manifests and plans | capability preserved; full production result not approved |
| InfiniteTalk local | local provider and setup UI | provider research and prior plan artifacts | code detected historically; no approved local benchmark/model bundle |
| InfiniteTalk RunPod | RunPod provider health | configuration contract and GPU runbook | submission intentionally disabled; no automatic API claim |
| Manual lip-sync export | manual provider/export services | manual package metadata and job records | supported as controlled export/import |
| Face correction | project tools and workflow documentation | bake-off, DLight iteration state, progress and model comparisons | HiFiFace 256 and UniFace 256 retained for accepted-clip comparison |
| Local capabilities | discovery, FFmpeg, model/provider health services | capability audits, benchmark records, system-tool reports | historical presence does not guarantee a new host is configured |
| System tools | FFmpeg/FFprobe discovery and health | reports, build logs, codec/playback evidence | binaries stay local; requirements and behavior are documented |
| Connectors | connector services and integration adapters | status YAML, provider matrices, security/license research | most generation remains manual unless explicitly configured |
| Studio Loop | orchestration, gates, defects, repair, budget, events | run/evaluation/approval/artifact state and database export | preserved under Advanced; never runs during `/create` GET |
| Director runs | run services and templates | all lightweight run files, plans, questions, decisions and evaluations | history preserved; old run success does not equal current acceptance |
| Storyboard/local generation | storyboard model and shot-pack services | storyboards, AI variants, shot packs, generated requests, render adapters | current Rescue storyboard/prompt set is primary |
| Animatics/playback | animatic and sync services | run metadata, reports, timing evidence and rescue deliverables | clean full-song rescue animatic is the current visual baseline |
| Result import/QC | result services, media probing, approval and QC | result state, selected/rejected decisions, audits and failure memory | source remains untouched; accepted managed copies drive rebuild |
| Motion references | motion library and reference services | motion metadata and prior movement rules | lead performance is singing-led; wider cinematic movement is allowed |
| Burmese voice | voice/setup services | voice records and decision history | caption-only/manual paths preserved; no fake voice or timing claim |
| Audit/failure memory | audit and evaluation services | failure/success registers, project map, selected clip inventory, safe EDL | must be read before reactivating rejected material |
| Privacy/rights | asset policy and security logic | privacy policy, license matrices, reference rights notes | private references and media remain outside Git |

## Database preservation

`research-history/advanced-database/director_os.sql` is a text export of the
local Director OS database at backup time. It retains the old Advanced
transactional records without committing a live SQLite binary. The test database
schema is in `test_schema.sql`.

The dump is historical. Restore it into a new database for inspection; do not
overwrite a newer workstation database. Absolute paths inside it are provenance
and may not exist on a GPU server.

## Full lightweight state

`research-history/full-director-os-state/` is a media-free mirror of every
textual Director OS artifact with these retained formats:

- Markdown, JSON, TXT, CSV;
- YAML/YML and TOML;
- Python and shell scripts;
- SRT, VTT, and ASS caption data.

Audio, video, images, databases, model weights, caches, and environments are not
silently omitted: their metadata, hashes, decisions, and local locations are
retained, while the binary payload remains on the private workstation.

## Non-negotiable interpretation

- “Preserved” means evidence and implementation are available.
- “Configured” does not mean operational.
- “Technically valid” does not mean human-approved.
- “Generated” does not mean accepted.
- A storyboard composite is always labeled composite, never AI-generated frame.
- A prior timing decision invalidated by real review stays invalidated.
- Advanced work can inform the creative product but cannot block the storyboard,
  clean animatic, prompts, import, or visual refinement.

