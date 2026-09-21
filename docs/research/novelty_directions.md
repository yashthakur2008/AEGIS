# AEGIS Paper Novelty Directions

## Field snapshot

Cold atmospheric plasma (CAP) is actively studied for wound disinfection and healing because reactive oxygen and nitrogen species can reduce bioburden while supporting healing pathways when dose is controlled. Recent clinical and review literature emphasizes a persistent gap: devices often apply fixed exposure schedules, while wound size, geometry, standoff distance, and tissue tolerance vary patient-to-patient. That makes closed-loop, image-guided dosing a credible research contribution for AEGIS.

Relevant directions from the current literature:

- CAP wound therapy reviews highlight antimicrobial and healing benefits, but also call out dose optimization and safety characterization as ongoing challenges.
- Clinical studies such as prospective tolerability work and the POWER chronic-wound RCT frame CAP as promising but needing indication-specific application modes.
- Robotics and camera calibration literature supports converting image detections into robot coordinates through fiducials or calibration grids, which maps directly to the Pixy2/gantry architecture already documented in this repo.

## Novel research angles AEGIS can add

1. **Image-guided adaptive CAP dosing**
   - Detect wound centroid/area/extent from Pixy2 or CV input.
   - Convert geometry into gantry coordinates.
   - Modulate plasma intensity and dwell time based on normalized wound area, confidence, and safety caps.
   - Novelty: moves from fixed CAP exposure to repeatable, geometry-aware dose planning.

2. **Low-cost Pixy2-controlled dermatology gantry**
   - Demonstrate a complete low-cost pipeline using accessible hardware instead of expensive clinical robotics.
   - Quantify coordinate error after calibration and treatment coverage over wound-shaped targets.
   - Novelty: practical, reproducible device architecture for educational/low-resource labs.

3. **Safety-first closed-loop treatment constraints**
   - CAP disabled by default.
   - Motion-only dry-run mode.
   - Intensity clamps, confidence thresholds, standoff limits, emergency STOP path.
   - Novelty: a formal safety envelope for image-guided CAP robotics.

4. **Treatment planning comparison study**
   - Compare centroid-only, raster-fill, and contour-following strategies on wound masks.
   - Metrics: coverage, path length, total dwell, estimated dose uniformity, time to treatment.
   - Novelty: systematic method choice rather than just showing a working prototype.

5. **Calibration robustness study**
   - Evaluate pixel-to-mm homography/affine calibration under marker noise, camera shifts, and lighting changes.
   - Use printed fiducials or known calibration points.
   - Novelty: validates whether Pixy2 is enough and when a depth/LiDAR sensor becomes necessary.

6. **Specialized onboard model without external APIs**
   - Train a small segmentation/classification model on wound-like phantoms or curated local images.
   - Keep inference local and deterministic.
   - For this repo's immediate step, use a model-compatible interface so learned perception can replace Pixy detections later without changing actuation.

## Recommended paper framing

Position AEGIS as an **image-guided adaptive CAP treatment robot**. The core research question can be:

> Can a low-cost gantry robot use camera-derived wound geometry to produce calibrated, safety-constrained motion and adaptive CAP intensity plans with repeatable target coverage?

Suggested experiments:

- Calibration accuracy: pixel target to gantry target error in mm.
- Coverage: percent of wound phantom area within planned CAP footprint.
- Dose adaptation: intensity/dwell changes monotonically with wound area and confidence while respecting safety limits.
- Robustness: performance under lighting/marker perturbations.
- Safety: verify STOP, disabled-by-default plasma behavior, and command clamping.

## Sources to cite or inspect further

- Reviews on cold atmospheric plasma in wound healing and RONS-mediated mechanisms.
- Prospective tolerability studies of CAP wound dressings/devices.
- POWER trial literature on CAP in chronic wounds.
- Pixy2 documentation for 60 FPS local color/object detection.
- Robot camera-to-coordinate calibration examples using grids/fiducials.
