from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

DepthLabel = Literal["surface", "shallow", "moderate", "deep_risk"]


@dataclass(frozen=True)
class DepthEstimate:
    depth_hint: DepthLabel
    z_offset_hint_mm: float
    confidence: float
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class WoundDetection:
    label: str
    confidence: float
    x_px: float
    y_px: float
    width_px: float
    height_px: float
    area_px2: float
    redness_score: float = 0.0
    depth: DepthEstimate | None = None

    @property
    def centroid_x_px(self) -> float:
        return self.x_px + self.width_px / 2.0

    @property
    def centroid_y_px(self) -> float:
        return self.y_px + self.height_px / 2.0

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["centroid_x_px"] = self.centroid_x_px
        payload["centroid_y_px"] = self.centroid_y_px
        if self.depth is not None:
            payload["depth"] = self.depth.to_dict()
            payload["depth_hint"] = self.depth.depth_hint
            payload["z_offset_hint_mm"] = self.depth.z_offset_hint_mm
        return payload


def detections_to_csv_rows(detections: list[WoundDetection]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for detection in detections:
        rows.append(
            {
                "centroid_x_px": detection.centroid_x_px,
                "centroid_y_px": detection.centroid_y_px,
                "area_px2": detection.area_px2,
                "confidence": detection.confidence,
                "label": detection.label,
                "depth_hint": detection.depth.depth_hint if detection.depth else "surface",
                "z_offset_hint_mm": detection.depth.z_offset_hint_mm if detection.depth else 0.0,
            }
        )
    return rows
