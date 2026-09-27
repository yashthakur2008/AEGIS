import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autonomous_movement.calibration import CalibrationSample, XYCalibration, solve_affine
from autonomous_movement.movement import Detection, detection_to_move_command, plan_move_commands


def test_solve_affine_maps_pixel_points_to_machine_xy():
    calibration = solve_affine(
        [
            CalibrationSample(120, 90, 0, 0),
            CalibrationSample(520, 90, 100, 0),
            CalibrationSample(120, 390, 0, 75),
            CalibrationSample(520, 390, 100, 75),
        ]
    )

    x_mm, y_mm = calibration.image_to_machine(300, 220)

    assert round(x_mm, 3) == 45.000
    assert round(y_mm, 3) == 32.500


def test_detection_to_move_command_keeps_z_fixed_for_xy_only_stage():
    calibration = XYCalibration(a=0.25, b=0, c=-30, d=0, e=0.25, f=-22.5)

    command = detection_to_move_command(Detection(300, 220, 2500, 0.9), calibration)

    assert command == "MOVE 45.000 32.500 0.000"


def test_plan_move_commands_handles_multiple_detections():
    calibration = XYCalibration(a=1, b=0, c=0, d=0, e=1, f=0)

    commands = plan_move_commands([Detection(1, 2), Detection(3, 4)], calibration)

    assert commands == ["MOVE 1.000 2.000 0.000", "MOVE 3.000 4.000 0.000"]
