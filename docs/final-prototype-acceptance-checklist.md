# AEGIS prototype acceptance checklist

Use this checklist to carry the roadmap through a complete workflow. Do not mark a phase complete unless the evidence column is filled with a screenshot, log path, test output, or commit hash.

## Phase 0: safety and startup

| Check | Pass condition | Evidence |
|---|---|---|
| CAP/plasma power disconnected | Physical power path is disconnected before camera, jog, or dry-run tests | |
| Dashboard server starts | `http://127.0.0.1:8766/dashboard` returns 200 | |
| Detector status available | `/cv-status.json` returns `ok: true` and `last_error: null` | |
| Regression tests pass | `python -m pytest -q` passes | |
| Browser hard refresh done | Dashboard loads current JS, not cached JS | |

## Phase 1: stabilized dashboard

| Check | Pass condition | Evidence |
|---|---|---|
| Smooth live feed | Browser camera feed is visually smooth while inference is running | |
| YOLO-only detection | Local color tracker remains disabled | |
| Skin negative case | Normal skin does not create a wound box | |
| Wound positive case | Printed/sample wound creates a wound box | |
| Close/mid/far cases | Detector result is recorded for all three distances | |
| Depth wording | UI clearly says relative/monocular depth only | |
| Latency visibility | UI or logs show request latency / last error | |

## Phase 2: copy/paste sample wound detector

| Check | Pass condition | Evidence |
|---|---|---|
| Clipboard paste | User can paste an image directly into detector panel | |
| Drag/drop | User can drag an image onto detector panel | |
| File upload | User can choose an image file | |
| Multiple wound support | One image can return `wound_count > 1` and separate boxes | |
| Negative examples | Background/skin sample returns `is_wound: false` | |
| Sample replay set | Local smoke-test set has wound, skin, background, far, close, multi-wound cases | |

## Phase 3: Logitech integration

| Check | Pass condition | Evidence |
|---|---|---|
| Device enumeration | Dashboard lists available cameras | |
| Logitech selectable | Logitech appears and can be selected by label/deviceId | |
| Laptop fallback | Laptop camera still works after Logitech selection | |
| Resolution chosen | Selected Logitech resolution/FPS is documented | |
| Smooth Logitech feed | Feed is smooth while inference runs | |
| Logitech calibration | Far/working/near/close relative depth buckets are recalibrated for Logitech geometry | |

## Phase 4: motion and safety dry run

| Check | Pass condition | Evidence |
|---|---|---|
| STOP tested | STOP command is visible and tested | |
| HOME tested | HOME / limit-switch zeroing is tested | |
| Jog commands tested | X/Y/Z jog works in simulator or hardware-safe mode | |
| Target-center overlay | Dashboard shows wound offset from target center | |
| Suggested jog vector | Dashboard suggests X/Y correction without automatic execution | |
| Autonomous Z blocked | No code path moves Z from monocular depth | |
| Dry-run only | CAP/plasma power remains disconnected during alignment demo | |

## Phase 5: final demo rehearsal

| Check | Pass condition | Evidence |
|---|---|---|
| Clean startup | Demo starts from a clean session using documented steps | |
| Sample detector demo | Positive, negative, and multi-wound samples work | |
| Logitech live demo | Logitech live wound detection works | |
| Motion dry-run demo | Suggested alignment workflow is shown safely | |
| Logs captured | Detector status and command logs are saved | |
| Screens/video captured | Final evidence is captured for fallback | |
| Limitations documented | Known limitations and safety disclaimers are documented | |
| Final branch/tag | Final demo branch or tag is frozen | |

## Minimum final prototype definition

The final prototype is acceptable when phases 0 through 5 are complete, evidence is attached for every row, and no safety row is blank.
