from __future__ import annotations

import json
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

from wound_cv_model.camera_server import CameraState, WoundCvHandler
from wound_cv_model.inference import HeuristicWoundDetector
from tools.sample_wound_smoke import SMOKE_CASES, run_smoke


def test_sample_wound_smoke_cases_are_representative():
    names = {case.name for case in SMOKE_CASES}

    assert "printed_wound_positive" in names
    assert "normal_skin_negative" in names
    assert "background_negative" in names
    assert "far_wound" in names
    assert "close_wound" in names
    assert "multi_wound" in names


def test_sample_wound_smoke_report_passes(tmp_path: Path):
    report = run_smoke(tmp_path, write_images=True)

    assert report["ok"] is True
    assert report["case_count"] == 7
    assert report["failures"] == []
    assert "do not drive autonomous Z" in str(report["depth_warning"])

    cases = {case["name"]: case for case in report["cases"]}
    assert cases["normal_skin_negative"]["count"] == 0
    assert cases["background_negative"]["count"] == 0
    assert cases["multi_wound"]["count"] >= 2
    assert (tmp_path / "sample_wound_smoke_report.json").exists()
    assert len(list((tmp_path / "images").glob("*.jpg"))) == 7

    saved = json.loads((tmp_path / "sample_wound_smoke_report.json").read_text(encoding="utf-8"))
    assert saved["ok"] is True


def test_sample_wound_smoke_can_replay_through_http_endpoint(tmp_path: Path):
    state = CameraState(camera_index=99)
    state.detector = HeuristicWoundDetector(min_area_px=120.0)

    class TestHandler(WoundCvHandler):
        camera_state = state

        def log_message(self, format, *args):  # noqa: A002, N802
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint_url = f"http://127.0.0.1:{server.server_address[1]}/cv-detect-frame"

    try:
        report = run_smoke(tmp_path, write_images=False, endpoint_url=endpoint_url)
    finally:
        server.shutdown()
        server.server_close()

    assert report["ok"] is True
    assert report["mode"] == "http_endpoint"
    assert report["endpoint_url"] == endpoint_url
    cases = {case["name"]: case for case in report["cases"]}
    assert cases["normal_skin_negative"]["server_is_wound"] is False
    assert cases["background_negative"]["server_wound_count"] == 0
    assert cases["printed_wound_positive"]["server_ok"] is True
    assert cases["far_wound"]["count"] >= 1
    assert cases["close_wound"]["count"] >= 1
    assert cases["multi_wound"]["count"] >= 2

    saved = json.loads((tmp_path / "sample_wound_smoke_report.json").read_text(encoding="utf-8"))
    assert saved["mode"] == "http_endpoint"
