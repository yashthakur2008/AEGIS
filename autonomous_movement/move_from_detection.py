from __future__ import annotations

import argparse
from pathlib import Path

from autonomous_movement.calibration import XYCalibration
from autonomous_movement.movement import load_detections, plan_move_commands


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert CV/Pixy detections into motion-only Arduino MOVE commands.")
    parser.add_argument("detections_csv", type=Path, help="CSV with centroid_x_px,centroid_y_px,area_px2,confidence")
    parser.add_argument("--calibration", type=Path, default=Path("autonomous_movement/calibration.json"))
    parser.add_argument("--z-mm", type=float, default=0.0, help="Fixed Z placeholder. Keep 0 during X/Y-only bring-up.")
    parser.add_argument("--serial-port", help="Optional Arduino serial port. Omit to print commands only.")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()

    calibration = XYCalibration.from_json(args.calibration.read_text())
    commands = plan_move_commands(load_detections(args.detections_csv), calibration, z_mm=args.z_mm)

    if args.serial_port is None:
        for command in commands:
            print(command)
        return

    try:
        import serial  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover
        raise SystemExit("pyserial is required for --serial-port. Install with: python -m pip install pyserial") from exc

    with serial.Serial(args.serial_port, baudrate=args.baud, timeout=0.5, write_timeout=2) as port:
        for command in commands:
            port.write((command + "\n").encode("ascii"))
            response = port.readline().decode("ascii", errors="replace").strip()
            print(response or f"SENT {command}")


if __name__ == "__main__":
    main()
