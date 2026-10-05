import sys
from pathlib import Path
from io import StringIO

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from host.aegis_control import AffineCalibration, DryRunSerialPort, PlasmaPolicy, TreatmentPlanner, VisionDetection
from host.aegis_control.serial_client import AegisSerialClient
from host.aegis_control.cli import emit_or_send_commands


def test_affine_calibration_converts_pixy_centroid_to_machine_point():
    calibration = AffineCalibration.from_scale_offset(
        x_mm_per_px=0.5,
        y_mm_per_px=0.25,
        x_offset_mm=10,
        y_offset_mm=20,
        z_mm=4,
    )
    point = calibration.image_to_machine(VisionDetection(100, 80, 1200).centroid)
    assert point.x_mm == 60
    assert point.y_mm == 40
    assert point.z_mm == 4


def test_plasma_policy_scales_with_area_and_confidence_with_safety_threshold():
    policy = PlasmaPolicy(reference_area_px2=1000, min_intensity=0.2, max_intensity=0.8)
    low_conf = VisionDetection(0, 0, 1000, confidence=0.1)
    high_conf = VisionDetection(0, 0, 500, confidence=1.0)
    assert policy.intensity_for(low_conf) == 0.0
    assert policy.dwell_for(low_conf) == 0
    assert policy.intensity_for(high_conf) == 0.5
    assert policy.dwell_for(high_conf) == 1125


def test_treatment_planner_emits_motion_and_plasma_commands():
    planner = TreatmentPlanner(AffineCalibration.from_scale_offset(x_mm_per_px=1, y_mm_per_px=1))
    waypoint = planner.plan_detection(VisionDetection(12.3456, 7.0, 5000, confidence=1.0))
    assert waypoint.move_command() == "MOVE 12.346 7.000 4.000"
    assert waypoint.plasma_command() == "PLASMA 0.750 2000"


def test_cli_emit_or_send_commands_prints_motion_only_plan():
    output = StringIO()
    planner = TreatmentPlanner(AffineCalibration.from_scale_offset(x_mm_per_px=0.5, y_mm_per_px=0.25))

    emit_or_send_commands(
        [VisionDetection(100, 80, 1200)],
        planner,
        emit_plasma=False,
        serial_port=None,
        baud=115200,
        output=output,
    )

    assert output.getvalue().splitlines() == ["HOME", "MOVE 50.000 20.000 4.000", "STATUS"]


def test_dry_run_serial_port_simulates_motion_and_blocks_plasma_by_default():
    port = DryRunSerialPort()
    client = AegisSerialClient(port, enable_plasma=False, response_timeout_s=0.1)

    assert client.home().startswith("OK HOME")
    assert client.send_line("MOVE 12.000 3.500 4.000") == "OK MOVE X=12.000 Y=3.500 Z=4.000"
    assert client.send_line("PLASMA 0.5 1000") == "ERR PLASMA_DISABLED"
    assert client.status() == "OK STATUS X=12.000 Y=3.500 Z=4.000 HOMED=1 STOPPED=0"


def test_cli_emit_or_send_commands_can_use_simulated_controller():
    output = StringIO()
    planner = TreatmentPlanner(AffineCalibration.from_scale_offset(x_mm_per_px=0.5, y_mm_per_px=0.25))

    emit_or_send_commands(
        [VisionDetection(100, 80, 1200)],
        planner,
        emit_plasma=False,
        serial_port=None,
        baud=115200,
        output=output,
        simulate_controller=True,
    )

    assert output.getvalue().splitlines() == [
        "OK HOME X=0.000 Y=0.000 Z=4.000",
        "OK MOVE X=50.000 Y=20.000 Z=4.000",
        "OK STATUS X=50.000 Y=20.000 Z=4.000 HOMED=1 STOPPED=0",
    ]
