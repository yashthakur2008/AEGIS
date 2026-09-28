# AEGIS next-sprint execution plan

This is the immediate implementation slice after the prototype roadmap. It is ordered to reduce demo risk fastest.

## Sprint objective

Turn the roadmap into a working operator flow: dashboard baseline, paste/drop sample detector, and Logitech camera selection foundation.

## Week 1 / next 10 focused tasks

### 1. Dashboard status and operator UX

1. Add visible detector status fields:
   - detector mode
   - last request latency
   - last error
   - selected camera source
2. Add a restart/help panel:
   - detached server command
   - log file path
   - hard-refresh instruction
3. Add a target-center crosshair overlay that is clearly not a wound detection box.
4. Keep the STOP command visible in every live or dry-run workflow.

Definition of done:

- Dashboard shows status without opening dev tools or terminal.
- Operator can tell whether lag is camera, browser, or detector.

### 2. Sample wound detector panel

4. Move still-image detection into a separate panel from live camera.
5. Add clipboard paste support.
6. Add drag/drop support.
7. Keep file upload support.
8. Render a result table with:
   - `is_wound`
   - `wound_count`
   - per-wound confidence
   - centroid
   - relative depth hint
   - z-offset hint

Definition of done:

- User can paste a screenshot and get boxes without starting the live camera.
- Multiple wounds in one image render as multiple rows and boxes.

### 3. Smoke-test sample set

9. Create or document a local sample set:
   - printed wound positive
   - normal skin negative
   - background negative
   - far wound
   - close wound
   - multi-wound example
10. Add a replay/check script or manual checklist that records output JSON for each sample.

Definition of done:

- Positive and negative still images can be tested repeatedly before live camera testing.

### 4. Logitech groundwork

11. Add camera enumeration in the dashboard.
12. Add source selector using camera labels/deviceIds.
13. Keep laptop camera as fallback.

Definition of done:

- Once the Logitech is plugged in, the dashboard can select it without code changes.

## Evidence to capture during sprint

- Screenshot of dashboard status panel.
- Screenshot/GIF of paste detector panel.
- JSON output from sample replay set.
- Screenshot of camera selector with Logitech listed.
- Test output from `python -m pytest -q`.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Still-image detector works but live detector fails | Use sample detector as model-quality baseline, then debug camera/lighting separately |
| Logitech labels are hidden until permission granted | Request camera permission first, then enumerate devices again |
| Normal skin false positives return | Keep local color tracker disabled and tune YOLO confidence/filtering only with sample evidence |
| Depth gets over-trusted | UI labels stay `relative`; autonomous Z remains blocked |

## Stop condition

Stop the sprint when the sample detector and camera selector are usable. Do not start motion integration until these are done and accepted.
