from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ImagePoint:
    x_px: float
    y_px: float


@dataclass(frozen=True)
class MachinePoint:
    x_mm: float
    y_mm: float
    z_mm: float = 0.0


@dataclass(frozen=True)
class AffineCalibration:
    """2D affine image-pixel to gantry-mm calibration.

    x_mm = a*x_px + b*y_px + c
    y_mm = d*x_px + e*y_px + f
    """

    a: float
    b: float
    c: float
    d: float
    e: float
    f: float
    z_mm: float = 4.0

    def image_to_machine(self, point: ImagePoint) -> MachinePoint:
        return MachinePoint(
            x_mm=self.a * point.x_px + self.b * point.y_px + self.c,
            y_mm=self.d * point.x_px + self.e * point.y_px + self.f,
            z_mm=self.z_mm,
        )

    @classmethod
    def from_scale_offset(
        cls,
        *,
        x_mm_per_px: float,
        y_mm_per_px: float,
        x_offset_mm: float = 0.0,
        y_offset_mm: float = 0.0,
        z_mm: float = 4.0,
    ) -> "AffineCalibration":
        return cls(x_mm_per_px, 0.0, x_offset_mm, 0.0, y_mm_per_px, y_offset_mm, z_mm)
