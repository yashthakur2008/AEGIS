from __future__ import annotations

from .detection import DepthEstimate


def estimate_depth_hint(area_ratio: float, redness_score: float) -> DepthEstimate:
    """Return a conservative Z hint, not true monocular wound depth."""
    severity = max(0.0, min(1.0, area_ratio * 8.0 + redness_score * 0.45))
    if severity < 0.20:
        return DepthEstimate("surface", 0.0, 0.35, "Monocular appearance only; keep Z fixed until calibrated.")
    if severity < 0.42:
        return DepthEstimate("shallow", -0.25, 0.40, "Appearance suggests a shallow target; verify with physical Z calibration.")
    if severity < 0.68:
        return DepthEstimate("moderate", -0.60, 0.45, "Appearance suggests a deeper target; do not automate Z without calibration.")
    return DepthEstimate("deep_risk", -1.00, 0.50, "High-risk depth hint from appearance only; manual review required.")
