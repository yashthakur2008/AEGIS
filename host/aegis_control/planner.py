from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .calibration import AffineCalibration, ImagePoint, MachinePoint


@dataclass(frozen=True)
class VisionDetection:
    """Camera-side wound detection contract.

    This can be produced by Pixy2 color blocks, classical CV, or a future local
    wound segmentation model. No external AI APIs are required by this layer.
    """

    centroid_x_px: float
    centroid_y_px: float
    area_px2: float
    confidence: float = 1.0

    @property
    def centroid(self) -> ImagePoint:
        return ImagePoint(self.centroid_x_px, self.centroid_y_px)


@dataclass(frozen=True)
class Waypoint:
    point: MachinePoint
    intensity: float
    dwell_ms: int

    def move_command(self) -> str:
        return f"MOVE {self.point.x_mm:.3f} {self.point.y_mm:.3f} {self.point.z_mm:.3f}"

    def plasma_command(self) -> str:
        return f"PLASMA {self.intensity:.3f} {self.dwell_ms}"


@dataclass(frozen=True)
class PlasmaPolicy:
    min_intensity: float = 0.15
    max_intensity: float = 0.75
    min_dwell_ms: int = 250
    max_dwell_ms: int = 2000
    reference_area_px2: float = 5000.0
    min_confidence: float = 0.45

    def intensity_for(self, detection: VisionDetection) -> float:
        if detection.confidence < self.min_confidence:
            return 0.0
        area_ratio = max(0.0, min(detection.area_px2 / self.reference_area_px2, 1.0))
        confidence_scale = max(0.0, min(detection.confidence, 1.0))
        value = self.min_intensity + area_ratio * (self.max_intensity - self.min_intensity)
        return round(value * confidence_scale, 3)

    def dwell_for(self, detection: VisionDetection) -> int:
        if detection.confidence < self.min_confidence:
            return 0
        area_ratio = max(0.0, min(detection.area_px2 / self.reference_area_px2, 1.0))
        return round(self.min_dwell_ms + area_ratio * (self.max_dwell_ms - self.min_dwell_ms))


@dataclass(frozen=True)
class TreatmentPlanner:
    calibration: AffineCalibration
    plasma_policy: PlasmaPolicy = PlasmaPolicy()

    def plan_detection(self, detection: VisionDetection) -> Waypoint:
        machine_point = self.calibration.image_to_machine(detection.centroid)
        return Waypoint(
            point=machine_point,
            intensity=self.plasma_policy.intensity_for(detection),
            dwell_ms=self.plasma_policy.dwell_for(detection),
        )

    def plan(self, detections: Iterable[VisionDetection]) -> list[Waypoint]:
        return [self.plan_detection(detection) for detection in detections]
