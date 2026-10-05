from __future__ import annotations

from pathlib import Path

from tools import marker_scan


def test_marker_scan_skips_binary_and_generated_artifacts(tmp_path: Path, monkeypatch):
    (tmp_path / "docs").mkdir()
    pdf = tmp_path / "docs" / "report.pdf"
    pdf.write_bytes(b"%PDF " + b"X" * 3 + b" binary false positive")
    (tmp_path / ".pio" / "build").mkdir(parents=True)
    build = tmp_path / ".pio" / "build" / "firmware.o"
    build.write_bytes(("HA" + "CK binary false positive").encode("utf-8"))
    source = tmp_path / "source.py"
    source.write_text("print('clean')\n", encoding="utf-8")
    monkeypatch.setattr(marker_scan, "tracked_files", lambda repo_root: [pdf, build, source])

    assert marker_scan.scan_markers(tmp_path) == []


def test_marker_scan_reports_tracked_text_marker(tmp_path: Path, monkeypatch):
    source = tmp_path / "source.py"
    marker = "FIX" + "ME"
    source.write_text(f"# {marker} wire real camera\n", encoding="utf-8")
    monkeypatch.setattr(marker_scan, "tracked_files", lambda repo_root: [source])

    assert marker_scan.scan_markers(tmp_path) == [f"source.py:1:# {marker} wire real camera"]
