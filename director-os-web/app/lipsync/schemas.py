from __future__ import annotations


ELIGIBILITY_STATES = [
    "lipsync_required",
    "lipsync_optional",
    "lipsync_not_needed",
    "lipsync_unsafe",
    "instrumental_or_nonvocal",
    "face_not_visible",
    "face_too_small",
    "motion_too_complex",
    "source_identity_unstable",
    "source_not_final",
]

DECISIONS = [
    "accepted",
    "accepted_with_trim",
    "needs_lipsync_retry",
    "needs_face_correction",
    "needs_composite_repair",
    "rejected",
    "archived",
]

CRITICAL_FAILURES = [
    "wrong_identity",
    "severe_mouth_deformation",
    "obvious_audio_offset",
    "face_melting",
    "identity_drift",
    "unstable_teeth",
    "severe_flicker",
    "broken_source_background",
    "body_deformation",
    "visible_transition_discontinuity",
]
