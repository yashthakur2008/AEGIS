# CV/Plasma Automation Validation

Validated on: 2026-09-21

## Public interface workflow

A realistic CSV was run through the documented CLI:

```bash
python -m host.aegis_control.cli detections.csv \
  --x-mm-per-px 0.5 --y-mm-per-px 0.25 \
  --x-offset-mm 10 --y-offset-mm 20
```

Observed motion-only output:

```text
HOME
MOVE 60.000 40.000 4.000
MOVE 16.173 21.750 4.000
MOVE 170.000 70.000 4.000
STATUS
```

This confirms the default public path emits only firmware-supported motion commands and does not emit plasma commands.

With `--emit-plasma`, observed output was:

```text
HOME
MOVE 60.000 40.000 4.000
PLASMA 0.265 670
MOVE 16.173 21.750 4.000
PLASMA 0.750 2000
MOVE 170.000 70.000 4.000
PLASMA 0.000 0
STATUS
```

This confirms area/confidence-based intensity and dwell planning, including the low-confidence safety case producing zero plasma output.

## Integration boundaries

- Package import and public planner API were exercised with `from host.aegis_control import ...`.
- `AegisSerialClient.execute_waypoint()` was exercised at the serial boundary. Observed behavior: with `enable_plasma=False`, only `MOVE` is written. With `enable_plasma=True`, `MOVE` and `PLASMA` are written in order.
- CLI argument failure mode was exercised. Missing `--y-mm-per-px` exits with status 2 and argparse reports the required argument.
- Python packaging syntax was checked with `python -m compileall -q host`.

## Artifact checks

- `docs/context/lab_chat_2026-09-21.pdf` is a valid PDF 1.4 file with 2 pages and contains the chat context title.
- `docs/research/novelty_directions.md` contains the recommended research framing and experiment directions.

## Automated tests

```text
pytest -q
11 passed
```

## Firmware acceptance path

PlatformIO was installed at user level and the real firmware build command was run:

```bash
export PATH="$HOME/.local/bin:$PATH"
pio run
```

Observed result:

```text
PlatformIO Core, version 6.2.0
Processing megaatmega2560 (platform: atmelavr; board: megaatmega2560; framework: arduino)
Dependency Graph
|-- AccelStepper @ 1.64.0
Checking size .pio/build/megaatmega2560/firmware.elf
========================= [SUCCESS] Took 8.41 seconds =========================
```

This confirms the Arduino Mega firmware compiles with the MOVE/PLASMA controller changes. The remaining hardware-only acceptance step is uploading to the physical Arduino Mega and running a motion-only gantry dry run before enabling the plasma output.
