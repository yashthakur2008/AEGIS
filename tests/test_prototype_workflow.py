from __future__ import annotations

from pathlib import Path

from check_prototype_workflow import check_workflow, format_results


def test_prototype_workflow_docs_pass_current_repo():
    repo_root = Path(__file__).resolve().parents[1]

    results = check_workflow(repo_root)

    assert all(result.ok for result in results), format_results(results)


def test_prototype_workflow_reports_missing_required_phrase(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "prototype-roadmap.md").write_text("PixyMon screen capture\n", encoding="utf-8")
    (docs / "final-prototype-acceptance-checklist.md").write_text("", encoding="utf-8")
    (docs / "next-sprint-plan.md").write_text("", encoding="utf-8")

    results = check_workflow(tmp_path)

    assert any(not result.ok for result in results)
    assert "FAIL" in format_results(results)
