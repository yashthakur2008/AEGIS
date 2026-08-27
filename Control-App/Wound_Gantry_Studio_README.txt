WOUND GANTRY STUDIO - MOTION-ONLY TEST

OPEN THE APPLICATION
1. Upload WoundGantry_XY_Pixy2_Calibrated_V7.ino to the Arduino Mega once.
2. Close Arduino Serial Monitor and close PixyMon.
3. Connect the Arduino and Pixy2 to the laptop with separate USB cables.
4. Double-click WoundGantryStudio.exe.
5. Open 1 MAIN CONTROL, select the Arduino COM port, and click Connect.
6. Press H or click Limit-switch home before any other motion.

MAIN CONTROL
- Main Control contains only gantry controls, the PixyCam live stream, and
  Arduino errors/faults.
- After connecting and homing, click X-, X+, Y-, or Y+ to move 5 mm per click.
- The arrow buttons remain disabled until the Arduino reports that homing completed.
- Upload the current firmware once before using the new directional buttons.

CAMERA AND PIXY2 SETTINGS
- Open 2 PIXYCAM SETUP. This screen contains only Pixy2/PixyMon controls.
- Click Attach camera here to dock the full PixyMon interface inside the app.
- If docking does not work, click Open in own window; all Pixy2 settings remain available.
- Train signatures from PixyMon's Action menu and use its gear button for camera settings.
- Choose which trained signatures mean wound and calibration marker in Firmware mapping,
  then click Save mapping to code and compile/upload the firmware.
- Leave Data out port set to Arduino ICSP SPI.
- The Pixy2 ribbon cable remains connected to the Arduino.

ARDUINO CODE
- Click 4 ARDUINO CODE or press F6.
- Edit the loaded .ino file.
- Save and Compile before uploading.
- Compile + Upload releases the COM port automatically.
- Uploading resets the Arduino. Reconnect and home again afterward.

MACHINE SETUP
- Click 3 MACHINE SETUP to edit driver pulses/revolution, X/Y screw lead,
  travel limits, homing speed, joystick speed, tracing speed, acceleration,
  corner-test speed, and safety margin.
- Motor STEP/DIR pins, X/Y limit-switch pins, and the joystick push-button pin
  can also be changed here. Each pin must be unique.
- Pins 50-53 are reserved for Pixy2 SPI, and pins 65-66 are the joystick axes.
- Steps/mm is calculated automatically from pulses/revolution divided by lead.
- Click Apply + save code, then compile and upload from the Arduino Code tab.
- The physical driver switch setting must match the pulses/revolution value.

GITHUB AND VERSION HISTORY
- Click 5 VERSIONS.
- Choose the outputs folder and initialize its dedicated repository.
- Enter your Git display name, email, and a version message.
- Save a version locally before pushing.
- Create an empty repository at GitHub, paste its HTTPS .git URL, and push.
- GitHub may open a secure browser sign-in. The app does not store tokens.

CALIBRATION USED
- Lead screw: 8 mm/revolution
- Driver: 1600 pulses/revolution
- Scale: 200 steps/mm
- Workspace: X 12 inches, Y 8 inches

SAFETY
- This application and firmware are for motion-only testing.
- Keep the plasma source disabled while testing, calibrating, or uploading code.
- Verify both axes have clear travel before running the four-corner test.
