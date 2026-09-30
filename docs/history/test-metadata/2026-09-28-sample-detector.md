# 2026-09-28 test metadata checkpoint: sample detector

Purpose: preserve the chronological validation trail for still-image wound detector requirements.

Recorded checks:

- Attached images should report `is_wound`, `wound_count`, per-wound boxes, centroids, confidence, and relative depth hints.
- Negative examples should be able to report `wound_count=0`.
- Live camera feed and still-image analysis should remain separate workflows.

This is a dated metadata checkpoint, not rewritten git history.
