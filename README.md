# Director OS — Burmese Music Video

Private development backup for the Director OS rescue studio and the music video
**The Bar Remembers Her**.

## Current creative direction

- Adult wife performs alone in the established dark-teak Finnish bar.
- Mature, emotionally intense singing performance; no dance choreography.
- Only natural micro-movement: breathing, small weight shifts, restrained head and
  shoulder response.
- Deep-red Burmese-inspired one-shoulder dress, realistic body proportions,
  amber/crimson light, and a Finnish winter window.
- Burmese art, architecture, cultural materials, quiet band coverage, sparse
  mature audience, and exterior winter cutaways can expand the world.
- No karaoke staging, microphone-centred lounge performance, martial arts, K-pop,
  TikTok movement, identity drift, generic replacement, body/rear emphasis, or
  child-containing references.
- Gemini lip-sync is not treated as reliable. Mouth-safe performance holds and
  cutaways are used until timing and face correction are approved.

The revised creative documents live in `creative-direction/`. The complete
24-shot prompt packages and storyboard metadata live in `rescue-studio/`.

## Rescue Studio

The FastAPI application is in `director-os-web/`.

- `/` redirects to `/create`.
- `/create` uses cached summaries and lightweight thumbnails.
- Long create/import/rebuild operations run as background jobs.
- Audio Truth remains preserved under Advanced and does not block creative work.
- The clean animatic has no unverified Burmese captions.

Local start command:

```bash
cd director-os-web
./scripts/run_local.sh
```

Then open `http://127.0.0.1:8787/create`.

## Important local-only assets

Large media, trained models, caches, and personal identity references are
intentionally excluded from GitHub. They remain in the original workstation at:

- `/Users/chan/song-video-project/references/`
- `/Users/chan/song-video-project/director-os/projects/burmese-music-video/`
- `/Users/chan/song-video-project/production/`
- `/Users/chan/song-video-project/face-correction/`
- `/Users/chan/song-video-project/local-tools/`

This includes the canonical master song, corrected Unicode lyric source,
approved wife A1/A2 references, body/wardrobe B, bar C, Burmese world E, generated
images and clips, full animatics, face-correction models, and provider exports.
Do not delete those local folders after cloning this repository.

The two approved face workflows remain:

- HiFiFace 256
- UniFace 256

Current trained wife model directories:

- `face-correction/work/models/p03-wife-dlight-v1/`
- `face-correction/v2/models/p03-wife-dlight-384-v2/`

## Continue the production

1. Generate the replacement portrait, restrained band, and sparse mature audience
   clips using `creative-direction/GEMINI_FIRST_GENERATION.md` and supporting
   prompts.
2. Keep acceptable existing environment/object clips.
3. Exclude all dancing clips from the active edit without deleting them.
4. Import new results through `/create`; assign inferred shots and rebuild.
5. Face-correct only accepted performer clips with the approved models.
6. Approve caption timing and lip-sync separately, after the visual edit works.

No third-party automatic generation is claimed. Gemini/Flow remains a manual
export/import workflow unless explicit API access is configured later.

## Storage

See `docs/STORAGE_CLEANUP_AUDIT.md`. Nothing was deleted when this repository was
prepared.

