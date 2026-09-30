from __future__ import annotations

import json
from pathlib import Path

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
    assert report["case_count"] == 6
    assert report["failures"] == []
    assert "do not drive autonomous Z" in str(report["depth_warning"])

    cases = {case["name"]: case for case in report["cases"]}
    assert cases["normal_skin_negative"]["count"] == 0
    assert cases["background_negative"]["count"] == 0
    assert cases["multi_wound"]["count"] >= 2
    assert (tmp_path / "sample_wound_smoke_report.json").exists()
    assert len(list((tmp_path / "images").glob("*.jpg"))) == 6

    saved = json.loads((tmp_path / "sample_wound_smoke_report.json").read_text(encoding="utf-8"))
    assert saved["ok"] is True
