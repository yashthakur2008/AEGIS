from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import TextIO

from .calibration import AffineCalibration
from .planner import PlasmaPolicy, TreatmentPlanner, VisionDetection
from .serial_client import AegisSerialClient
from .simulator import DryRunSerialPort

REQUIRED_DETECTION_FIELDS = ("centroid_x_px", "centroid_y_px", "area_px2")


def load_detections(path: Path) -> list[VisionDetection]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = set(reader.fieldnames or [])
        missing_fields = [field for field in REQUIRED_DETECTION_FIELDS if field not in fieldnames]
        if missing_fields:
            raise ValueError(f"{path}: missing required detection CSV column(s): {', '.join(missing_fields)}")

        detections: list[VisionDetection] = []
        for line_number, row in enumerate(reader, start=2):
            try:
                detections.append(
                    VisionDetection(
                        centroid_x_px=float(row["centroid_x_px"]),
                        centroid_y_px=float(row["centroid_y_px"]),
                        area_px2=float(row["area_px2"]),
                        confidence=float(row.get("confidence") or 1.0),
                    )
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"{path}: invalid numeric detection value on CSV line {line_number}: "
                    "centroid_x_px, centroid_y_px, area_px2, and confidence must be numbers"
                ) from exc
        return detections


def load_detections_or_exit(path: Path) -> list[VisionDetection]:
    try:
        return load_detections(path)
    except OSError as exc:
        raise SystemExit(f"Could not read detections CSV {path}: {exc}") from exc
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def emit_or_send_commands(
    detections: list[VisionDetection],
    planner: TreatmentPlanner,
    *,
    emit_plasma: bool,
    serial_port: str | None,
    baud: int,
    output: TextIO,
    simulate_controller: bool = False,
) -> None:
    waypoints = planner.plan(detections)
    if simulate_controller:
        simulator = DryRunSerialPort(allow_plasma=emit_plasma)
        client = AegisSerialClient(simulator, enable_plasma=emit_plasma, response_timeout_s=0.1)
        print(client.home(), file=output)
        for waypoint in waypoints:
            for response in client.execute_waypoint(waypoint):
                print(response, file=output)
        print(client.status(), file=output)
        return

    if serial_port is None:
        print("HOME", file=output)
        for waypoint in waypoints:
            print(waypoint.move_command(), file=output)
            if emit_plasma:
                print(waypoint.plasma_command(), file=output)
        print("STATUS", file=output)
        return

    try:
        import serial  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on local tooling
        raise SystemExit("pyserial is required for --serial-port. Install with: python -m pip install pyserial") from exc

    with serial.Serial(serial_port, baudrate=baud, timeout=0.5, write_timeout=2) as port:
        client = AegisSerialClient(port, enable_plasma=emit_plasma, response_timeout_s=5.0)
        print(client.status(), file=output)
        for waypoint in waypoints:
            for response in client.execute_waypoint(waypoint):
                print(response, file=output)
        print(client.status(), file=output)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan AEGIS gantry and plasma commands from CV detections.")
    parser.add_argument("detections_csv", type=Path)
    parser.add_argument("--x-mm-per-px", type=float, required=True)
    parser.add_argument("--y-mm-per-px", type=float, required=True)
    parser.add_argument("--x-offset-mm", type=float, default=0.0)
    parser.add_argument("--y-offset-mm", type=float, default=0.0)
    parser.add_argument("--z-mm", type=float, default=4.0)
    parser.add_argument("--emit-plasma", action="store_true", help="Print PLASMA commands after MOVE commands.")
    parser.add_argument("--serial-port", help="Send planned MOVE commands to an Arduino serial port instead of printing only.")
    parser.add_argument("--simulate-controller", action="store_true", help="Run commands through an in-memory firmware line-protocol simulator instead of hardware.")
    parser.add_argument("--baud", type=int, default=115200, help="Arduino serial baud when --serial-port is used.")
    args = parser.parse_args()

    calibration = AffineCalibration.from_scale_offset(
        x_mm_per_px=args.x_mm_per_px,
        y_mm_per_px=args.y_mm_per_px,
        x_offset_mm=args.x_offset_mm,
        y_offset_mm=args.y_offset_mm,
        z_mm=args.z_mm,
    )
    planner = TreatmentPlanner(calibration=calibration, plasma_policy=PlasmaPolicy())
    emit_or_send_commands(
        load_detections_or_exit(args.detections_csv),
        planner,
        emit_plasma=args.emit_plasma,
        serial_port=args.serial_port,
        baud=args.baud,
        output=__import__("sys").stdout,
        simulate_controller=args.simulate_controller,
    )


if __name__ == "__main__":
    main()
