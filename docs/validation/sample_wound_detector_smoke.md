# Sample wound detector smoke workflow

This workflow gives the dashboard sample detector a repeatable baseline before live Logitech or laptop-camera testing.

## What it covers

The smoke set is synthetic and deterministic:

1. `printed_wound_positive` should detect at least one wound-like region.
2. `normal_skin_negative` should detect zero wounds.
3. `background_negative` should detect zero wounds.
4. `far_wound` should detect a small wound-like target.
5. `close_wound` should detect a large wound-like target.
6. `multi_wound` should detect multiple wound-like regions.

These images are not a model-quality substitute for real pasted photos. They are a workflow check that verifies the still-image detector can process positives, negatives, close/far targets, and multi-wound images in a stable way.

## Run it

```bash
python tools/sample_wound_smoke.py --output-dir sample_outputs --write-images
```

Outputs:

- `sample_outputs/sample_wound_smoke_report.json`
- `sample_outputs/images/*.jpg` when `--write-images` is used

## Dashboard replay

1. Start the dashboard at `http://127.0.0.1:8766/dashboard`.
2. Drag one generated image from `sample_outputs/images/` onto the **Sample wound detector** panel, or use **Attach / Analyze Wound Image**.
3. Confirm the result table shows one row per wound candidate.
4. Paste a screenshot/image with `Cmd+V` to test the clipboard path.
5. Confirm negative cases show `wound_count=0, is_wound=false`.

## Safety note

Relative depth and Z hints in this workflow are visual labels only. They must not drive autonomous Z motion without real calibration or depth hardware.
