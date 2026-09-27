from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class CalibrationSample:
    pixel_x: float
    pixel_y: float
    machine_x_mm: float
    machine_y_mm: float


@dataclass(frozen=True)
class XYCalibration:
    """Affine transform from image pixels to machine X/Y millimeters.

    machine_x_mm = a*pixel_x + b*pixel_y + c
    machine_y_mm = d*pixel_x + e*pixel_y + f
    """

    a: float
    b: float
    c: float
    d: float
    e: float
    f: float

    def image_to_machine(self, pixel_x: float, pixel_y: float) -> tuple[float, float]:
        return (
            self.a * pixel_x + self.b * pixel_y + self.c,
            self.d * pixel_x + self.e * pixel_y + self.f,
        )

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_json(cls, text: str) -> "XYCalibration":
        return cls(**json.loads(text))


def load_samples(path: Path) -> list[CalibrationSample]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            CalibrationSample(
                pixel_x=float(row["pixel_x"]),
                pixel_y=float(row["pixel_y"]),
                machine_x_mm=float(row["machine_x_mm"]),
                machine_y_mm=float(row["machine_y_mm"]),
            )
            for row in reader
        ]


def solve_affine(samples: Iterable[CalibrationSample]) -> XYCalibration:
    points = list(samples)
    if len(points) < 3:
        raise ValueError("At least 3 calibration points are required for an affine transform")

    # Least-squares solve for [a,b,c] and [d,e,f] using normal equations.
    rows = [[p.pixel_x, p.pixel_y, 1.0] for p in points]
    xtx = [[sum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)]
    xt_x = [sum(row[i] * p.machine_x_mm for row, p in zip(rows, points)) for i in range(3)]
    xt_y = [sum(row[i] * p.machine_y_mm for row, p in zip(rows, points)) for i in range(3)]
    ax = _solve_3x3(xtx, xt_x)
    ay = _solve_3x3(xtx, xt_y)
    return XYCalibration(ax[0], ax[1], ax[2], ay[0], ay[1], ay[2])


def _solve_3x3(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    augmented = [row[:] + [value] for row, value in zip(matrix, rhs)]
    for pivot in range(3):
        best = max(range(pivot, 3), key=lambda r: abs(augmented[r][pivot]))
        if abs(augmented[best][pivot]) < 1e-9:
            raise ValueError("Calibration points are degenerate. Use points spread across the workspace.")
        augmented[pivot], augmented[best] = augmented[best], augmented[pivot]
        scale = augmented[pivot][pivot]
        for col in range(pivot, 4):
            augmented[pivot][col] /= scale
        for row in range(3):
            if row == pivot:
                continue
            factor = augmented[row][pivot]
            for col in range(pivot, 4):
                augmented[row][col] -= factor * augmented[pivot][col]
    return [augmented[i][3] for i in range(3)]
