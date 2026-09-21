# AEGIS Paper Hypotheses and Next-Day Data Plan

Purpose: give the team a paper-ready experimental frame that can be adapted directly during the next lab session. The safest publishable angle is **image-guided, safety-constrained adaptive CAP planning on a low-cost gantry**, not a clinical efficacy claim.

## Draft paper thesis

AEGIS demonstrates that a low-cost Pixy2/CV-guided gantry can convert wound-like image detections into calibrated motion and conservative plasma intensity/dwell commands, enabling repeatable target coverage and safety-bounded adaptive CAP treatment planning.

## Primary research question

Can camera-derived wound geometry be converted into calibrated gantry motion and adaptive CAP dose commands with repeatable accuracy, coverage, and safety behavior on a low-cost dermatological robot?

## Hypotheses

### H1: Camera-to-gantry calibration accuracy

**Hypothesis:** After a basic pixel-to-mm calibration, AEGIS can place the treatment head within a small, repeatable error bound of camera-detected wound phantom targets.

- **Independent variable:** calibration condition and target location.
- **Dependent variable:** absolute target error in millimeters.
- **Suggested acceptance target:** mean error <= 5 mm and max error <= 10 mm for paper/demo-grade validation. Tighten after observing real hardware.
- **Why it matters:** establishes that image detections can be trusted enough to drive treatment planning.

### H2: Adaptive plasma planning follows wound geometry

**Hypothesis:** Planned plasma intensity and dwell time increase monotonically with detected wound area while remaining clamped inside predefined safety limits.

- **Independent variable:** wound phantom area in image pixels or measured mm².
- **Dependent variables:** planned intensity, planned dwell time, total planned exposure.
- **Suggested acceptance target:** Spearman correlation > 0.9 between wound area and planned dwell/intensity for above-confidence detections, with no command exceeding the configured maximum.
- **Why it matters:** supports the novelty claim that AEGIS is adaptive rather than fixed-dose.

### H3: Low-confidence detections suppress plasma output

**Hypothesis:** The planner suppresses plasma commands when CV confidence falls below the safety threshold.

- **Independent variable:** detection confidence.
- **Dependent variable:** emitted plasma intensity and dwell.
- **Suggested acceptance target:** all detections below threshold emit `PLASMA 0.000 0` or no plasma command, depending on test mode.
- **Why it matters:** establishes safety-first behavior for uncertain perception.

### H4: Motion-only dry-run reproduces planned path

**Hypothesis:** With plasma disabled, the gantry can execute planned waypoints in the expected order without limit-triggered interruption or serial protocol errors.

- **Independent variable:** planned path type: centroid-only, raster, contour-following if available.
- **Dependent variables:** command success rate, observed waypoint completion, runtime, STOP responsiveness.
- **Suggested acceptance target:** 100% valid command parsing and no unexpected limit hits during bounded dry-run paths.
- **Why it matters:** validates the physical workflow before CAP exposure.

### H5: Treatment coverage improves over centroid-only targeting

**Hypothesis:** Raster or contour-following plans cover a larger percentage of wound phantom area than a single centroid-only exposure at comparable or bounded total exposure.

- **Independent variable:** planning strategy.
- **Dependent variables:** estimated coverage percentage, path length, total dwell, runtime.
- **Suggested acceptance target:** raster/contour coverage exceeds centroid-only coverage by >= 20 percentage points on irregular wound phantoms.
- **Why it matters:** turns the project from a working demo into a comparative research study.

### H6: Robustness under lighting and marker perturbations

**Hypothesis:** Calibration and detection remain within acceptable error under moderate lighting changes and small marker/camera perturbations.

- **Independent variable:** lighting condition, camera offset, marker visibility.
- **Dependent variables:** detection confidence, target error, failed detection rate.
- **Suggested acceptance target:** target error remains within 2x baseline and failure rate stays below 10% under moderate perturbations.
- **Why it matters:** anticipates reviewer concerns about Pixy2/CV reliability.

## Data to collect next lab day

### 1. Calibration dataset

| Trial | Date/time | Camera | Calibration method | Target pixel x | Target pixel y | Commanded x mm | Commanded y mm | Observed x mm | Observed y mm | Error mm | Notes |
|------:|-----------|--------|--------------------|---------------:|---------------:|---------------:|---------------:|-------------:|-------------:|---------:|-------|
| 1 | | Pixy2/CV | scale-offset / affine | | | | | | | | |

**How to collect:** place a printed grid or marked phantom under the camera. Detect or manually record pixel positions, command the gantry to converted coordinates, then measure actual head position relative to target.

### 2. Detection and wound phantom dataset

| Phantom ID | Shape | Measured area mm² | Pixel area | Centroid x px | Centroid y px | Confidence | Lighting condition | Detection success? | Notes |
|------------|-------|------------------:|-----------:|--------------:|--------------:|-----------:|--------------------|--------------------|-------|
| A | circle / oval / irregular | | | | | | baseline | yes/no | |

**How to collect:** use at least 3 shapes and 3 sizes. Include one irregular shape because it better supports the coverage/planning argument.

### 3. Planner output dataset

| Trial | Phantom ID | Planner mode | x mm | y mm | z mm | Intensity | Dwell ms | Total planned exposure | Safety clamp triggered? | Notes |
|------:|------------|--------------|-----:|-----:|-----:|----------:|---------:|-----------------------:|-------------------------|-------|
| 1 | | centroid | | | | | | | yes/no | |

**How to collect:** run the same detection CSV through the host planner with and without `--emit-plasma`. Save the terminal output and the input CSV.

### 4. Motion dry-run dataset

| Trial | Planner mode | Waypoints sent | Waypoints completed | Runtime s | Serial errors | Limit hits | STOP tested? | Pass/fail | Notes |
|------:|--------------|---------------:|--------------------:|----------:|--------------:|-----------:|-------------|-----------|-------|
| 1 | centroid / raster / contour | | | | | | yes/no | | |

**How to collect:** keep plasma physically disabled. Home first, stream planned `MOVE` commands, observe gantry path, then test `STOP` at least once in a safe region.

### 5. Coverage dataset

| Phantom ID | Planner mode | CAP footprint diameter mm | Estimated covered area mm² | Phantom area mm² | Coverage % | Path length mm | Total dwell ms | Runtime s | Notes |
|------------|--------------|--------------------------:|---------------------------:|-----------------:|-----------:|---------------:|---------------:|----------:|-------|
| A | centroid | | | | | | | | |
| A | raster | | | | | | | | |

**How to collect without live plasma:** estimate coverage using the planned head positions and an assumed CAP footprint circle. This is acceptable for a planning study if clearly labeled as estimated treatment coverage.

### 6. Safety dataset

| Test | Expected result | Observed result | Pass/fail | Notes |
|------|-----------------|-----------------|-----------|-------|
| Boot with plasma disabled | PWM output off | | | |
| Motion-only CLI mode | no `PLASMA` commands | | | |
| Low confidence detection | zero plasma output | | | |
| STOP command | motion target held and plasma disabled | | | |
| Out-of-range coordinate | firmware clamps to travel bounds | | | |
| Limit switch trigger | motion stops away from limit | | | |

## Minimum viable experiment for tomorrow

If time is limited, collect this smaller dataset:

1. **Calibration:** 9 grid points, 3 repeated trials each.
2. **Phantoms:** 3 wound-like shapes: small circle, large oval, irregular blob.
3. **Planner:** run each phantom through motion-only and plasma-output CLI modes.
4. **Motion dry-run:** execute one centroid path per phantom with plasma disabled.
5. **Safety:** verify boot-disabled plasma, low-confidence suppression, and STOP.

This is enough to support an initial paper claim about a validated image-to-coordinate-to-dose planning pipeline.

## Suggested figures and tables

- **Figure 1:** System pipeline diagram: Pixy2/CV -> calibration -> planner -> serial firmware -> gantry/CAP head.
- **Figure 2:** Calibration grid with target vs observed points.
- **Figure 3:** Example wound phantom detections with centroids and planned waypoints.
- **Figure 4:** Dose adaptation plot: wound area vs planned intensity/dwell.
- **Figure 5:** Planner comparison: centroid vs raster/contour estimated coverage.
- **Table 1:** Hardware and software components.
- **Table 2:** Calibration accuracy summary: mean, median, max error.
- **Table 3:** Safety tests and pass/fail outcomes.

## Analysis formulas

- **Position error:** `sqrt((observed_x_mm - commanded_x_mm)^2 + (observed_y_mm - commanded_y_mm)^2)`
- **Coverage percentage:** `estimated_covered_area_mm2 / phantom_area_mm2 * 100`
- **Command success rate:** `successful_commands / total_commands * 100`
- **Detection failure rate:** `failed_detections / total_trials * 100`
- **Dose monotonicity:** Spearman correlation between wound area and planned dwell/intensity.

## Paper-ready claims to use only if data supports them

- AEGIS converted camera-space wound detections into gantry-space treatment coordinates with mean error of `__ mm`.
- The planner produced safety-clamped, geometry-aware plasma commands whose dwell/intensity scaled monotonically with wound phantom area.
- Low-confidence detections were suppressed by design, preventing unintended plasma output.
- Motion-only dry runs completed `__ / __` planned waypoints without serial errors or unexpected limit hits.
- Compared with centroid-only targeting, `raster/contour` planning improved estimated wound coverage from `__%` to `__%`.

## Do not claim yet

- Do not claim clinical wound healing efficacy without biological/clinical data.
- Do not claim sterilization or bacterial reduction unless microbial assays are run.
- Do not claim autonomous treatment is safe for humans. Phrase as bench-top phantom validation.
- Do not imply plasma was safely applied unless the CAP driver, standoff, thermal monitoring, and interlocks are validated.

## Manuscript scaffold

Use this structure to turn the data plan into the paper quickly.

### Working title

**AEGIS: A Low-Cost Image-Guided Gantry for Safety-Constrained Adaptive Cold Atmospheric Plasma Treatment Planning**

### Abstract skeleton

- **Background:** CAP is promising for wound care, but fixed exposure workflows do not adapt to wound geometry or perception uncertainty.
- **Objective:** Present a low-cost image-guided gantry workflow that converts wound-like detections into calibrated motion and safety-clamped plasma planning commands.
- **Methods:** Use Pixy2/CV detections, pixel-to-mm calibration, a host planner, Arduino Mega gantry firmware, and phantom wound targets. Evaluate calibration error, command success, estimated coverage, dose monotonicity, and safety behavior.
- **Results:** Fill in after lab data: calibration error, waypoint success rate, coverage improvement, intensity/dwell monotonicity, and safety test outcomes.
- **Conclusion:** AEGIS supports bench-top image-guided adaptive CAP planning and provides a reproducible platform for future biological validation.

### Introduction outline

1. Clinical motivation: chronic wounds, infection control, and need for precise treatment.
2. CAP background: antimicrobial and wound-healing relevance, with dose/safety challenges.
3. Robotics gap: many CAP workflows are fixed-position or fixed-dose rather than geometry-aware.
4. AEGIS contribution: low-cost camera-to-gantry-to-dose planning pipeline.
5. Scope boundary: bench-top phantom validation, not clinical efficacy.

### Methods outline

1. Hardware: 3-axis gantry, Arduino Mega, stepper drivers, Pixy2/CV input, CAP head placeholder/control output.
2. Software: `VisionDetection`, `AffineCalibration`, `TreatmentPlanner`, serial firmware protocol.
3. Calibration: grid/marker procedure and error calculation.
4. Planning: centroid/raster/contour strategy depending on what is tested.
5. Safety controls: plasma disabled by default, confidence threshold, intensity clamp, STOP, limit switches.
6. Metrics: calibration error, command success, coverage, path length, dwell/intensity, runtime, safety pass/fail.

### Results outline

- Calibration accuracy table and target-vs-observed plot.
- Planner output table showing monotonic dose behavior.
- Motion dry-run command success table.
- Coverage comparison between centroid-only and raster/contour plans.
- Safety checklist table.

### Discussion outline

- Interpret whether Pixy2/CV accuracy is sufficient for phantom treatment planning.
- Explain how adaptive planning improves over fixed exposure.
- Discuss limitations: no clinical data, CAP biological efficacy not tested, calibration sensitivity, hardware safety still needs full interlock validation.
- Future work: local segmentation model, depth/LiDAR support, thermal feedback, microbial assays, live CAP characterization.

## Next code/data improvements

- Add a `data/experiments/YYYY-MM-DD/` folder for raw CSVs and photos.
- Add a small analysis notebook or script to compute calibration error and coverage tables.
- Add a raster/contour planner mode if the team wants the strongest paper comparison.
- Add local model training only after collecting labeled wound phantom images. Keep it offline and specialized, not API-based.
