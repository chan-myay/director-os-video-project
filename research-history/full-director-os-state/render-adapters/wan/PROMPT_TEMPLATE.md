# Wan Adapter Template

Status: template only. Do not run Wan or create final prompts yet.

Later mapping from `RENDERER_FIELDS.yaml`:

- `references.identity` -> character image input
- `motion.reference_clip` -> pose/motion/background plate if available
- `location` -> background preservation or target plate rules
- `negative_rules` -> rejection checklist

Wan is best suited to staged replacement tests, not random generation.
