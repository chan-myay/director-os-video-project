# Batch C Face Classification

Rule: no close clear face shot is approved here. Any close/medium face use
requires normal-speed moving review and local correction review. Classifications
below are conservative.

## Classifications

### C01

File:
`production/selected/batch-c/C01_verse1-stable-medium_SELECTED.mp4`

Classification: use only after HiFiFace.

Reason: medium emotional face is visible. It may be useful for verse emotion,
but should not be approved before HiFiFace moving review.

### C02

File:
`production/selected/batch-c/C02_verse1-frontal-close_SELECTED.mp4`

Classification: use only after HiFiFace.

Reason: frontal close face has high identity risk. It should not be used in
v2C except as a placeholder for future face-corrected review.

### C03

File:
`production/selected/batch-c/C03_verse1-threequarter-emotion_SELECTED.mp4`

Classification: use only after HiFiFace.

Reason: three-quarter emotional face is visible enough to require correction
review.

### C04

File:
`production/selected/batch-c/C04_pre-chorus-hand-heart_SELECTED.mp4`

Classification: use only after HiFiFace.

Reason: hand/heart gesture can be useful, but face is still visible. If used
before correction, crop/cover with object edits where possible.

### C05

File:
`production/selected/batch-c/C05_chorus-emotional-front_SELECTED.mp4`

Classification: no use for final lip-sync.

Reason: documented generated mouth/performance movement. It can only be used as
a very short hidden/covered energy placeholder, not as an approved singing shot.

### C06

File:
`production/selected/batch-c/C06_chorus-silent-emotional-hold_SELECTED.mp4`

Classification: use only after HiFiFace.

Reason: close/medium emotional face is visible. Use only as punctuation after
identity correction review.

### C07 Original

File:
`production/selected/batch-c/C07_profile-memory-look_SELECTED.mp4`

Classification: no use.

Reason: first 0-2 seconds are documented weak identity. Use trimmed version
instead.

### C07 Trimmed

File:
`production/selected/batch-c/C07_profile-memory-look_SELECTED_use-after-00-02.mp4`

Classification: wide/medium only.

Reason: profile/memory use is acceptable only after the weak first 2 seconds
are removed. Keep it brief and avoid treating it as identity-approved close
face.

### C08

File:
`production/selected/batch-c/C08_tearful-close-eye-detail_SELECTED.mp4`

Classification: object/eye/detail only.

Reason: close detail can support emotion but should avoid full-face identity
approval until correction review.

### C09

File:
`production/selected/batch-c/C09_chorus-performance-wide_SELECTED-stage-continuity-face-caution.mp4`

Classification: wide/medium only.

Reason: stage continuity is useful, but face changes are documented. Use only
where face remains small and not a hero identity read.

### C10

File:
`production/selected/batch-c/C10_final-still-resolve_SELECTED.mp4`

Classification: use only after HiFiFace.

Reason: final emotional resolve exposes face. It needs correction review before
final use.

## UniFace Use

UniFace is the approved backup model. Use UniFace tests only if HiFiFace review
fails on a specific continuous shot group or creates artifacts. Do not switch
between HiFiFace and UniFace inside one continuous shot.
