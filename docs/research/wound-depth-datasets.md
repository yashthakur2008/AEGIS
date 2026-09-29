# Wound depth dataset candidates for Z-axis calibration

Goal: identify datasets that can teach or validate relative wound depth for later Z-axis accuracy work. This is for calibration/research only. Monocular depth is still not safe for autonomous Z motion until calibrated with the actual Logitech/camera mount.

## Best candidate: Syn3DWound

- Name: **Syn3DWound: A Synthetic Dataset for 3D Wound Bed Analysis**
- Page: <https://lebrat.github.io/Syn3DWound/>
- Dataset DOI: <https://doi.org/10.25919/5rwz-ts17>
- Paper: <https://arxiv.org/abs/2311.15836>
- Why it fits: it is openly available and includes realistic synthetic wound images with **2D and 3D annotations**, segmentation masks, and wound bed geometry.
- Best use in AEGIS: train/validate relative wound depth buckets and wound bed shape features before collecting our own Logitech calibration data.
- Limitation: synthetic domain gap. It will not replace calibration from the real Logitech camera, lighting, print/skin target, and gantry mounting geometry.

## Supporting reference: RGB-D wound measurement literature

- Non-Invasive 3D Wound Measurement with RGB-D Imaging: <https://arxiv.org/abs/2601.19014>
- RGB-D Camera-Based Automatic Wound-Measurement System: IEEE paper, DOI page surfaced in search.
- Why it matters: these works validate the direction of using RGB-D or 3D reconstruction for wound surface area, perimeter, and geometry.
- Limitation: not necessarily packaged as easy-to-use public training data.

## Non-depth datasets useful only for segmentation/classification

- WoundTissue dataset: <https://github.com/akabircs/WoundTissue>
- UWM wound segmentation resources: <https://github.com/uwm-bigdata/wound-segmentation>
- Kaggle wound segmentation images: <https://www.kaggle.com/datasets/leoscode/wound-segmentation-images>

These are useful for wound/tissue segmentation but do **not** solve Z-axis calibration by themselves.

## Proposed calibration path

1. Use Syn3DWound to prototype 3D-aware labels: `far`, `working`, `near`, `close`, wound bed geometry, and relative depth/risk features.
2. Add a calibration capture workflow in the dashboard using the Logitech camera:
   - capture target at known distances,
   - record camera device, resolution, and measured distance,
   - save detection area, centroid, confidence, and manual distance label.
3. Fit a simple camera-specific mapping from apparent wound size and segmentation shape to relative Z buckets.
4. Keep Z output as a **suggestion** until validated against physical measurements.
5. Only after repeatable calibration, consider motion suggestions. Autonomous Z remains blocked.

## Immediate next implementation task

Add dashboard capture metadata for Logitech calibration samples:

- camera source/device label,
- resolution,
- known distance bucket,
- detection JSON,
- screenshot/image filename,
- timestamp.
