from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


REQUIRED_DOCS = {
    "roadmap": Path("docs/prototype-roadmap.md"),
    "acceptance_checklist": Path("docs/final-prototype-acceptance-checklist.md"),
    "next_sprint_plan": Path("docs/next-sprint-plan.md"),
}

REQUIRED_ROADMAP_PHRASES = [
    "PixyMon screen capture",
    "multiple wounds in one image",
    "relative calibration hint",
    "Do not drive autonomous Z",
    "Stabilize the wound CV dashboard",
    "Build copy/paste sample wound detector",
    "Move vision from laptop camera to Logitech camera",
    "Integrate motion controls with vision safety gates",
    "Final integrated AEGIS prototype demo",
]

REQUIRED_CHECKLIST_PHASES = [
    "Phase 0: safety and startup",
    "Phase 1: stabilized dashboard",
    "Phase 2: copy/paste sample wound detector",
    "Phase 3: Logitech integration",
    "Phase 4: motion and safety dry run",
    "Phase 5: final demo rehearsal",
]

REQUIRED_NEXT_SPRINT_ITEMS = [
    "Dashboard status and operator UX",
    "Sample wound detector panel",
    "Smoke-test sample set",
    "Logitech groundwork",
    "STOP command visible",
    "Keep local color tracker disabled",
]


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def _contains_all(path: Path, phrases: list[str]) -> list[CheckResult]:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    results: list[CheckResult] = []
    for phrase in phrases:
        results.append(CheckResult(f"{path}:{phrase}", phrase in text, "present" if phrase in text else "missing"))
    return results


def check_workflow(repo_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    for name, relative in REQUIRED_DOCS.items():
        path = repo_root / relative
        results.append(CheckResult(name, path.exists(), str(relative)))

    roadmap = repo_root / REQUIRED_DOCS["roadmap"]
    checklist = repo_root / REQUIRED_DOCS["acceptance_checklist"]
    next_sprint = repo_root / REQUIRED_DOCS["next_sprint_plan"]

    results.extend(_contains_all(roadmap, REQUIRED_ROADMAP_PHRASES))
    results.extend(_contains_all(checklist, REQUIRED_CHECKLIST_PHASES))
    results.extend(_contains_all(next_sprint, REQUIRED_NEXT_SPRINT_ITEMS))
    return results


def format_results(results: list[CheckResult]) -> str:
    lines = []
    for result in results:
        mark = "PASS" if result.ok else "FAIL"
        lines.append(f"{mark} {result.name} - {result.detail}")
    passed = sum(1 for result in results if result.ok)
    lines.append(f"SUMMARY {passed}/{len(results)} checks passed")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate AEGIS prototype roadmap workflow artifacts.")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    results = check_workflow(args.repo_root)
    print(format_results(results))
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
