from __future__ import annotations

from pathlib import Path


def test_wound_depth_dataset_research_names_3d_candidate_and_limits():
    doc = (Path(__file__).resolve().parents[1] / "docs" / "research" / "wound-depth-datasets.md").read_text(encoding="utf-8")

    assert "Syn3DWound" in doc
    assert "2D and 3D annotations" in doc
    assert "https://doi.org/10.25919/5rwz-ts17" in doc
    assert "Logitech" in doc
    assert "Autonomous Z remains blocked" in doc
    assert "synthetic domain gap" in doc
