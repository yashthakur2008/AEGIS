using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.IO.Ports;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace WoundGantryControl
{
    internal sealed class ScrollFriendlyNumericUpDown : NumericUpDown
    {
        protected override void OnMouseWheel(MouseEventArgs e)
        {
            Control current = Parent;
            while (current != null)
            {
                var scrollable = current as ScrollableControl;
                if (scrollable != null && scrollable.AutoScroll)
                {
                    Point position = scrollable.AutoScrollPosition;
                    int x = Math.Max(0, -position.X);
                    int y = Math.Max(0, -position.Y - e.Delta);
                    scrollable.AutoScrollPosition = new Point(x, y);
                    return;
                }
                current = current.Parent;
            }
            base.OnMouseWheel(e);
        }
    }

    internal static class Program
    {
        [DllImport("shcore.dll")]
        private static extern int SetProcessDpiAwareness(int awareness);

        [DllImport("user32.dll")]
        private static extern bool SetProcessDPIAware();

        [STAThread]
        private static void Main()
        {
            try
            {
                // Per-monitor DPI awareness prevents Windows from bitmap-stretching
                // the entire interface on high-resolution laptop displays.
                if (SetProcessDpiAwareness(2) != 0) SetProcessDPIAware();
            }
            catch
            {
                try { SetProcessDPIAware(); } catch { }
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            MainForm form = new MainForm();
            Application.Run(form);
        }
    }

    internal sealed class MainForm : Form
    {
        private const int GwlStyle = -16;
        private const int WsCaption = 0x00C00000;
        private const int WsThickFrame = 0x00040000;
        private const int WsChild = 0x40000000;
        private const int WsVisible = 0x10000000;
        private const int SwRestore = 9;

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr SetParent(IntPtr child, IntPtr newParent);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int GetWindowLong(IntPtr window, int index);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern int SetWindowLong(IntPtr window, int index, int value);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern bool MoveWindow(IntPtr window, int x, int y, int width, int height, bool repaint);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr window, int command);

        private readonly Color Navy = Color.FromArgb(16, 40, 48);
        private readonly Color Teal = Color.FromArgb(20, 125, 126);
        private readonly Color PaleTeal = Color.FromArgb(226, 241, 239);
        private readonly Color Orange = Color.FromArgb(233, 104, 58);
        private readonly Color Paper = Color.FromArgb(247, 249, 248);
        private readonly Color Line = Color.FromArgb(219, 228, 229);

        private readonly string appDirectory;
        private readonly string pixyMonPath;
        private readonly string arduinoCliPath;
        private readonly string gitPath;
        private string sketchPath;

        private TabControl tabs;
        private Panel pixyHost;
        private Panel pixyLiveHost;
        private Panel pixySetupHost;
        private Label pixyStatus;
        private Button startPixyButton;
        private NumericUpDown woundSignatureInput;
        private NumericUpDown markerSignatureInput;
        private ComboBox portList;
        private Button connectButton;
        private Button homeButton;
        private Button cornersButton;
        private Button statusButton;
        private readonly List<Button> jogButtons = new List<Button>();
        private Label machineState;
        private TextBox arduinoErrorLog;
        private RichTextBox codeEditor;
        private TextBox buildOutput;
        private Label codePathLabel;
        private Button compileButton;
        private Button uploadButton;
        private ToolStripStatusLabel footerStatus;
        private readonly Dictionary<string, NumericUpDown> setupInputs = new Dictionary<string, NumericUpDown>();
        private Label xStepsResult;
        private Label yStepsResult;
        private TextBox gitFolderBox;
        private TextBox gitRemoteBox;
        private TextBox gitNameBox;
        private TextBox gitEmailBox;
        private TextBox gitCommitBox;
        private TextBox gitOutput;
        private Button gitInitializeButton;
        private Button gitCommitButton;
        private Button gitPushButton;

        private SerialPort serial;
        private Process pixyProcess;
        private bool startedPixy;
        private IntPtr pixyWindow = IntPtr.Zero;
        private int pixyOriginalStyle;
        private int dockAttempts;
        private System.Windows.Forms.Timer pixyTimer;
        private bool pixyStandaloneRequested;
        private bool buildBusy;

        public MainForm()
        {
            appDirectory = AppDomain.CurrentDomain.BaseDirectory;
            pixyMonPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "PixyMon v2", "bin", "PixyMon.exe");
            arduinoCliPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Arduino IDE", "resources", "app", "lib", "backend", "resources", "arduino-cli.exe");
            gitPath = FindGit();
            sketchPath = Path.Combine(appDirectory, "WoundGantry_XY_Pixy2_Calibrated_V7.ino");

            Text = "Wound Gantry Studio";
            StartPosition = FormStartPosition.CenterScreen;
            MinimumSize = new Size(1100, 720);
            Size = new Size(1450, 900);
            WindowState = FormWindowState.Maximized;
            BackColor = Paper;
            Font = new Font("Segoe UI", 9F);
            AutoScaleMode = AutoScaleMode.Dpi;
            DoubleBuffered = true;
            KeyPreview = true;

            BuildInterface();
            RefreshPorts();
            LoadSketch(sketchPath);

            KeyDown += MainFormKeyDown;
            FormClosing += MainFormClosing;
            Shown += delegate
            {
                tabs.SelectedIndex = 0;
                SwitchPixyHost(pixyLiveHost);
                StartOrAttachPixy();
            };
        }

        private void BuildInterface()
        {
            var shell = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 4, BackColor = Paper, Margin = new Padding(0), Padding = new Padding(0) };
            shell.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 64F));
            shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 62F));
            shell.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            shell.RowStyles.Add(new RowStyle(SizeType.Absolute, 27F));
            Controls.Add(shell);

            var header = new Panel { Dock = DockStyle.Fill, BackColor = Navy, Padding = new Padding(24, 9, 24, 9), Margin = new Padding(0) };
            var title = new Label { Text = "Wound Gantry Studio", ForeColor = Color.White, Font = new Font("Segoe UI Semibold", 18F, FontStyle.Bold), AutoSize = true, Location = new Point(24, 13) };
            header.Controls.Add(title);
            shell.Controls.Add(header, 0, 0);

            var navigation = new TableLayoutPanel { Dock = DockStyle.Fill, BackColor = Color.White, ColumnCount = 5, RowCount = 1, Padding = new Padding(14, 9, 14, 8), Margin = new Padding(0) };
            for (int index = 0; index < 5; index++) navigation.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 20F));
            navigation.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            string[] navigationText = { "1  MAIN CONTROL", "2  PIXYCAM SETUP", "3  MACHINE SETUP", "4  ARDUINO CODE", "5  VERSIONS" };
            for (int index = 0; index < navigationText.Length; index++)
            {
                int target = index;
                var button = new Button
                {
                    Text = navigationText[index],
                    Tag = index,
                    Dock = DockStyle.Fill,
                    Margin = new Padding(5, 0, 5, 0),
                    FlatStyle = FlatStyle.Flat,
                    BackColor = index == 0 ? Teal : Color.White,
                    ForeColor = index == 0 ? Color.White : Navy,
                    Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold),
                    Cursor = Cursors.Hand
                };
                button.FlatAppearance.BorderColor = index == 0 ? Teal : Line;
                button.Click += delegate { tabs.SelectedIndex = target; };
                navigation.Controls.Add(button, index, 0);
            }
            shell.Controls.Add(navigation, 0, 1);

            var statusStrip = new StatusStrip { BackColor = Navy, ForeColor = Color.White, SizingGrip = false };
            footerStatus = new ToolStripStatusLabel("Ready. Connect the Arduino, then home before motion.");
            statusStrip.Items.Add(footerStatus);
            shell.Controls.Add(statusStrip, 0, 3);

            tabs = new TabControl { Dock = DockStyle.Fill, Appearance = TabAppearance.FlatButtons, SizeMode = TabSizeMode.Fixed, ItemSize = new Size(0, 1), Margin = new Padding(0) };
            tabs.TabPages.Add(BuildMainTab());
            tabs.TabPages.Add(BuildPixyTab());
            tabs.TabPages.Add(BuildSetupTab());
            tabs.TabPages.Add(BuildCodeTab());
            tabs.TabPages.Add(BuildGitTab());
            tabs.SelectedIndexChanged += delegate
            {
                foreach (Control control in navigation.Controls)
                {
                    var button = control as Button;
                    if (button == null) continue;
                    bool selected = (int)button.Tag == tabs.SelectedIndex;
                    button.BackColor = selected ? Teal : Color.White;
                    button.ForeColor = selected ? Color.White : Navy;
                    button.FlatAppearance.BorderColor = selected ? Teal : Line;
                }
                if (tabs.SelectedIndex == 0)
                {
                    SwitchPixyHost(pixyLiveHost);
                    StartOrAttachPixy();
                }
                else if (tabs.SelectedIndex == 1)
                {
                    SwitchPixyHost(pixySetupHost);
                    StartOrAttachPixy();
                }
            };
            shell.Controls.Add(tabs, 0, 2);
        }

        private TabPage BuildMainTab()
        {
            var page = new TabPage("Main Control") { BackColor = Paper, Padding = new Padding(14) };
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 2, RowCount = 1, BackColor = Paper, Padding = new Padding(0), Margin = new Padding(0) };
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 370F));
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100F));
            page.Controls.Add(layout);

            var controls = new Panel { Dock = DockStyle.Fill, BackColor = Color.White, Padding = new Padding(18), AutoScroll = true, AutoScrollMinSize = new Size(345, 640), Margin = new Padding(0, 0, 12, 0) };
            layout.Controls.Add(controls, 0, 0);

            controls.Controls.Add(new Label { Text = "GANTRY CONTROL", ForeColor = Navy, Font = new Font("Segoe UI Semibold", 14F, FontStyle.Bold), AutoSize = true, Location = new Point(18, 15) });
            controls.Controls.Add(new Label { Text = "1. Select Arduino port", ForeColor = Color.FromArgb(99, 119, 128), AutoSize = true, Location = new Point(18, 50) });

            portList = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Location = new Point(18, 71), Width = 105, Font = new Font("Segoe UI", 10F) };
            var refresh = StyledButton("Refresh", Color.White, Navy, 78);
            refresh.FlatAppearance.BorderColor = Line;
            refresh.Location = new Point(132, 68);
            refresh.Click += delegate { RefreshPorts(); };
            connectButton = StyledButton("Connect", Teal, Color.White, 110);
            connectButton.Location = new Point(219, 68);
            connectButton.Click += delegate { ToggleSerial(); };
            controls.Controls.Add(portList);
            controls.Controls.Add(refresh);
            controls.Controls.Add(connectButton);

            machineState = new Label { Text = "● Disconnected · Not homed", ForeColor = Color.Firebrick, AutoSize = true, Location = new Point(18, 112), Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold) };
            controls.Controls.Add(machineState);

            homeButton = CommandButton("H", "2. Limit-switch home", "Find X0 and Y0, then back away", 145);
            homeButton.Click += delegate { SendCommand("H"); };
            controls.Controls.Add(homeButton);

            cornersButton = CommandButton("C", "3. Test four corners", "Home first, then check usable travel", 230);
            cornersButton.Click += delegate { ConfirmCorners(); };
            controls.Controls.Add(cornersButton);

            statusButton = StyledButton("Request Arduino status", PaleTeal, Color.FromArgb(11, 93, 95), 314);
            statusButton.Location = new Point(18, 317);
            statusButton.Click += delegate { SendCommand("STATUS"); };
            controls.Controls.Add(statusButton);

            var manual = new GroupBox { Text = "Clickable manual movement · 5 mm per click", Location = new Point(18, 369), Size = new Size(314, 235), ForeColor = Navy };
            var jogUp = PhysicalJogButton("▲\r\nY+", "Y+", 117, 28);
            var jogLeft = PhysicalJogButton("◀  X−", "X-", 28, 92);
            var jogRight = PhysicalJogButton("X+  ▶", "X+", 206, 92);
            var jogDown = PhysicalJogButton("Y−\r\n▼", "Y-", 117, 156);
            var center = new Label { Text = "5 mm", Size = new Size(70, 54), Location = new Point(122, 96), TextAlign = ContentAlignment.MiddleCenter, BackColor = PaleTeal, ForeColor = Teal, Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold) };
            manual.Controls.Add(jogUp);
            manual.Controls.Add(jogLeft);
            manual.Controls.Add(center);
            manual.Controls.Add(jogRight);
            manual.Controls.Add(jogDown);
            manual.Controls.Add(new Label { Text = "Home the gantry to enable these buttons.", AutoSize = true, ForeColor = Color.DimGray, Location = new Point(52, 214), Font = new Font("Segoe UI", 8F) });
            controls.Controls.Add(manual);

            var communication = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 3, BackColor = Paper, Margin = new Padding(0) };
            communication.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            communication.RowStyles.Add(new RowStyle(SizeType.Absolute, 46F));
            communication.RowStyles.Add(new RowStyle(SizeType.Percent, 70F));
            communication.RowStyles.Add(new RowStyle(SizeType.Percent, 30F));
            layout.Controls.Add(communication, 1, 0);

            var messagesHeading = new Panel { Dock = DockStyle.Fill, BackColor = Color.White, Padding = new Padding(16, 9, 16, 6), Margin = new Padding(0, 0, 0, 8) };
            messagesHeading.Controls.Add(new Label { Text = "LIVE PIXY2 CAMERA + ARDUINO ERRORS", ForeColor = Navy, Font = new Font("Segoe UI Semibold", 13F, FontStyle.Bold), AutoSize = true, Location = new Point(14, 9) });
            communication.Controls.Add(messagesHeading, 0, 0);

            var cameraGroup = new GroupBox { Text = "PixyCam live stream", Dock = DockStyle.Fill, ForeColor = Navy, Padding = new Padding(10), Margin = new Padding(0, 0, 0, 8) };
            pixyLiveHost = new Panel { Dock = DockStyle.Fill, BackColor = Navy, BorderStyle = BorderStyle.FixedSingle };
            pixyLiveHost.Controls.Add(new Label { Text = "Connecting to PixyMon live view...", Dock = DockStyle.Fill, ForeColor = Color.FromArgb(190, 215, 218), BackColor = Navy, TextAlign = ContentAlignment.MiddleCenter, Font = new Font("Segoe UI", 11F) });
            pixyLiveHost.Resize += delegate { if (pixyHost == pixyLiveHost) ResizeDockedPixy(); };
            cameraGroup.Controls.Add(pixyLiveHost);
            communication.Controls.Add(cameraGroup, 0, 1);

            var errorsGroup = new GroupBox { Text = "Arduino errors and faults", Dock = DockStyle.Fill, ForeColor = Color.Firebrick, Padding = new Padding(12), Margin = new Padding(0) };
            var clearErrors = StyledButton("Clear errors", Color.White, Color.Firebrick, 120);
            clearErrors.Dock = DockStyle.Bottom;
            clearErrors.FlatAppearance.BorderColor = Color.FromArgb(230, 190, 190);
            clearErrors.Click += delegate { arduinoErrorLog.Clear(); };
            arduinoErrorLog = new TextBox { Dock = DockStyle.Fill, Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Both, WordWrap = false, BackColor = Color.FromArgb(55, 24, 27), ForeColor = Color.FromArgb(255, 205, 205), Font = new Font("Consolas", 10F), BorderStyle = BorderStyle.FixedSingle };
            errorsGroup.Controls.Add(arduinoErrorLog);
            errorsGroup.Controls.Add(clearErrors);
            communication.Controls.Add(errorsGroup, 0, 2);

            SetMotionButtons(false);
            return page;
        }

        private TabPage BuildPixyTab()
        {
            var page = new TabPage("PixyCam Setup") { BackColor = Paper, Padding = new Padding(14) };
            var cameraPanel = new Panel { Dock = DockStyle.Fill, BackColor = Color.White, Padding = new Padding(16) };
            page.Controls.Add(cameraPanel);

            var cameraToolbar = new Panel { Dock = DockStyle.Top, Height = 174, BackColor = Color.White };
            var cameraTitle = new Label { Text = "LIVE PIXY2 CAMERA", ForeColor = Navy, Font = new Font("Segoe UI Semibold", 13F, FontStyle.Bold), AutoSize = true, Location = new Point(0, 0) };
            var cameraHelp = new Label { Text = "Use PixyMon's Action menu to set signatures and its gear button for camera settings.", ForeColor = Color.FromArgb(99, 119, 128), Font = new Font("Segoe UI", 9F), AutoSize = false, AutoEllipsis = true, Location = new Point(2, 28), Height = 20 };
            startPixyButton = StyledButton("Attach camera here", Teal, Color.White, 155);
            startPixyButton.Location = new Point(0, 47);
            startPixyButton.Click += delegate { StartOrAttachPixy(); };
            var openCamera = StyledButton("Open in own window", Color.White, Navy, 165);
            openCamera.FlatAppearance.BorderColor = Line;
            openCamera.Location = new Point(166, 47);
            openCamera.Click += delegate { OpenPixyStandalone(); };
            pixyStatus = new Label { Text = "● Camera not attached", ForeColor = Color.DimGray, AutoSize = false, AutoEllipsis = true, Location = new Point(2, 91), Height = 21, Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold) };
            cameraToolbar.Resize += delegate
            {
                cameraHelp.Width = Math.Max(180, cameraToolbar.ClientSize.Width - 4);
                pixyStatus.Width = Math.Max(180, cameraToolbar.ClientSize.Width - 4);
            };
            cameraToolbar.Controls.Add(cameraTitle);
            cameraToolbar.Controls.Add(cameraHelp);
            cameraToolbar.Controls.Add(startPixyButton);
            cameraToolbar.Controls.Add(openCamera);
            cameraToolbar.Controls.Add(pixyStatus);

            var signatureBar = new FlowLayoutPanel { Dock = DockStyle.Bottom, Height = 52, BackColor = PaleTeal, FlowDirection = FlowDirection.LeftToRight, WrapContents = false, Padding = new Padding(10, 9, 10, 7), AutoScroll = true };
            signatureBar.Controls.Add(new Label { Text = "Firmware mapping", ForeColor = Teal, Font = new Font("Segoe UI Semibold", 9F, FontStyle.Bold), AutoSize = true, Margin = new Padding(0, 7, 14, 0) });
            signatureBar.Controls.Add(new Label { Text = "Wound signature", ForeColor = Navy, AutoSize = true, Margin = new Padding(0, 7, 6, 0) });
            woundSignatureInput = new NumericUpDown { Minimum = 1, Maximum = 7, Value = 2, Width = 52, Font = new Font("Segoe UI", 9F, FontStyle.Bold), Margin = new Padding(0, 3, 16, 0) };
            signatureBar.Controls.Add(woundSignatureInput);
            signatureBar.Controls.Add(new Label { Text = "Marker signature", ForeColor = Navy, AutoSize = true, Margin = new Padding(0, 7, 6, 0) });
            markerSignatureInput = new NumericUpDown { Minimum = 1, Maximum = 7, Value = 1, Width = 52, Font = new Font("Segoe UI", 9F, FontStyle.Bold), Margin = new Padding(0, 3, 16, 0) };
            signatureBar.Controls.Add(markerSignatureInput);
            var saveMapping = StyledButton("Save mapping to code", Teal, Color.White, 175);
            saveMapping.Margin = new Padding(0, 0, 0, 0);
            saveMapping.Click += delegate { SavePixySignatureMapping(); };
            signatureBar.Controls.Add(saveMapping);
            cameraToolbar.Controls.Add(signatureBar);
            cameraPanel.Controls.Add(cameraToolbar);

            pixySetupHost = new Panel { Dock = DockStyle.Fill, BackColor = Navy, BorderStyle = BorderStyle.FixedSingle };
            pixyHost = pixySetupHost;
            var placeholder = new Label
            {
                Text = "PIXY2 / PIXYMON\r\n\r\nConnect Pixy2 to the laptop with USB, then click Attach camera here.\r\n\r\nSet color signatures from PixyMon's Action menu.\r\nOpen camera settings with PixyMon's gear button.",
                ForeColor = Color.FromArgb(190, 215, 218),
                BackColor = Navy,
                TextAlign = ContentAlignment.MiddleCenter,
                Dock = DockStyle.Fill,
                Font = new Font("Segoe UI", 12F, FontStyle.Regular)
            };
            pixySetupHost.Controls.Add(placeholder);
            pixySetupHost.Resize += delegate { if (pixyHost == pixySetupHost) ResizeDockedPixy(); };
            cameraPanel.Controls.Add(pixySetupHost);
            cameraToolbar.BringToFront();
            return page;
        }

        private TabPage BuildCodeTab()
        {
            var page = new TabPage("Arduino Code Editor") { BackColor = Paper, Padding = new Padding(10) };
            var layout = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = 1, RowCount = 5, BackColor = Paper, Padding = new Padding(0) };
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100F));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 58F));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 34F));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 72F));
            layout.RowStyles.Add(new RowStyle(SizeType.Absolute, 30F));
            layout.RowStyles.Add(new RowStyle(SizeType.Percent, 28F));
            page.Controls.Add(layout);

            var toolbar = new Panel { Dock = DockStyle.Fill, BackColor = Color.White, Padding = new Padding(10) };

            var open = StyledButton("Open .ino", Color.White, Navy, 90);
            open.FlatAppearance.BorderColor = Line;
            open.Location = new Point(10, 10);
            open.Click += delegate { OpenSketch(); };
            var save = StyledButton("Save", PaleTeal, Color.FromArgb(11, 93, 95), 75);
            save.Location = new Point(110, 10);
            save.Click += delegate { SaveSketch(); };
            compileButton = StyledButton("Compile", Teal, Color.White, 95);
            compileButton.Location = new Point(195, 10);
            compileButton.Click += async delegate { await RunArduinoCli(false); };
            uploadButton = StyledButton("Compile + Upload", Orange, Color.White, 140);
            uploadButton.Location = new Point(300, 10);
            uploadButton.Click += async delegate { await RunArduinoCli(true); };
            codePathLabel = new Label { AutoEllipsis = true, ForeColor = Color.DimGray, Location = new Point(458, 17), Size = new Size(720, 24), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };
            toolbar.Controls.Add(open);
            toolbar.Controls.Add(save);
            toolbar.Controls.Add(compileButton);
            toolbar.Controls.Add(uploadButton);
            toolbar.Controls.Add(codePathLabel);
            layout.Controls.Add(toolbar, 0, 0);

            var editorHeading = new Panel { Dock = DockStyle.Fill, BackColor = PaleTeal, Padding = new Padding(12, 7, 12, 4) };
            editorHeading.Controls.Add(new Label { Text = "ARDUINO SKETCH — CLICK BELOW AND TYPE TO EDIT", Dock = DockStyle.Fill, ForeColor = Teal, Font = new Font("Segoe UI", 9F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft });
            layout.Controls.Add(editorHeading, 0, 1);

            codeEditor = new RichTextBox { Dock = DockStyle.Fill, AcceptsTab = true, WordWrap = false, DetectUrls = false, Font = new Font("Consolas", 11F), BackColor = Color.White, ForeColor = Navy, BorderStyle = BorderStyle.FixedSingle, ScrollBars = RichTextBoxScrollBars.Both, HideSelection = false };
            layout.Controls.Add(codeEditor, 0, 2);

            var outputHeading = new Panel { Dock = DockStyle.Fill, BackColor = Color.White, Padding = new Padding(12, 5, 12, 3) };
            outputHeading.Controls.Add(new Label { Text = "COMPILER / UPLOAD MESSAGES", Dock = DockStyle.Fill, ForeColor = Teal, Font = new Font("Segoe UI", 9F, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft });
            layout.Controls.Add(outputHeading, 0, 3);

            buildOutput = new TextBox { Dock = DockStyle.Fill, Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Both, WordWrap = false, Font = new Font("Consolas", 9F), BackColor = Navy, ForeColor = Color.FromArgb(190, 230, 226) };
            layout.Controls.Add(buildOutput, 0, 4);
            return page;
        }

        private TabPage BuildSetupTab()
        {
            var page = new TabPage("Machine Setup") { BackColor = Paper, Padding = new Padding(18), AutoScroll = true, AutoScrollMinSize = new Size(1140, 930) };

            var title = new Label { Text = "MACHINE CALIBRATION & SPEEDS", ForeColor = Navy, Font = new Font("Segoe UI", 16F, FontStyle.Bold), AutoSize = true, Location = new Point(18, 16) };
            var description = new Label { Text = "Change the values here, apply them to the Arduino code, then compile and upload from the Arduino Code tab.", ForeColor = Color.DimGray, AutoSize = true, Location = new Point(20, 49) };
            page.Controls.Add(title);
            page.Controls.Add(description);

            var calibration = new GroupBox { Text = "Motion calibration", Location = new Point(18, 85), Size = new Size(520, 305), ForeColor = Navy, Font = new Font("Segoe UI", 10F, FontStyle.Bold) };
            AddSetupInput(calibration, 32, "X driver pulses/revolution", "DRIVER_PULSES_PER_REV_X", 1600M, 200M, 50000M, 0, "pulses/rev");
            AddSetupInput(calibration, 74, "Y driver pulses/revolution", "DRIVER_PULSES_PER_REV_Y", 1600M, 200M, 50000M, 0, "pulses/rev");
            AddSetupInput(calibration, 116, "X lead-screw travel", "LEAD_MM_PER_REV_X", 8M, 0.1M, 100M, 3, "mm/rev");
            AddSetupInput(calibration, 158, "Y lead-screw travel", "LEAD_MM_PER_REV_Y", 8M, 0.1M, 100M, 3, "mm/rev");

            var resultPanel = new Panel { Location = new Point(16, 210), Size = new Size(486, 76), BackColor = PaleTeal };
            resultPanel.Controls.Add(new Label { Text = "Calculated scale", ForeColor = Teal, Font = new Font("Segoe UI", 9F, FontStyle.Bold), AutoSize = true, Location = new Point(14, 10) });
            xStepsResult = new Label { Text = "X: 200 steps/mm", ForeColor = Navy, Font = new Font("Segoe UI", 11F, FontStyle.Bold), AutoSize = true, Location = new Point(14, 37) };
            yStepsResult = new Label { Text = "Y: 200 steps/mm", ForeColor = Navy, Font = new Font("Segoe UI", 11F, FontStyle.Bold), AutoSize = true, Location = new Point(250, 37) };
            resultPanel.Controls.Add(xStepsResult);
            resultPanel.Controls.Add(yStepsResult);
            calibration.Controls.Add(resultPanel);
            page.Controls.Add(calibration);

            var motion = new GroupBox { Text = "Workspace and speeds", Location = new Point(558, 85), Size = new Size(540, 430), ForeColor = Navy, Font = new Font("Segoe UI", 10F, FontStyle.Bold) };
            AddSetupInput(motion, 32, "X usable travel", "X_MAX_MM", 304.8M, 1M, 2000M, 2, "mm");
            AddSetupInput(motion, 74, "Y usable travel", "Y_MAX_MM", 203.2M, 1M, 2000M, 2, "mm");
            AddSetupInput(motion, 116, "Homing speed", "HOME_SPEED_MM_S", 5M, 0.1M, 100M, 2, "mm/s");
            AddSetupInput(motion, 158, "Homing backoff", "HOME_BACKOFF_MM", 3M, 0.1M, 50M, 2, "mm");
            AddSetupInput(motion, 200, "Maximum joystick speed", "JOG_MAX_MM_S", 15M, 0.1M, 250M, 2, "mm/s");
            AddSetupInput(motion, 242, "Wound tracing speed", "TRACE_MM_S", 8M, 0.1M, 250M, 2, "mm/s");
            AddSetupInput(motion, 284, "Acceleration", "ACCEL_MM_S2", 25M, 0.1M, 1000M, 2, "mm/s²");
            AddSetupInput(motion, 326, "Corner-test speed", "CORNER_TEST_MM_S", 15M, 0.1M, 250M, 2, "mm/s");
            AddSetupInput(motion, 368, "Corner safety margin", "CORNER_MARGIN_MM", 5M, 0.1M, 100M, 2, "mm");
            page.Controls.Add(motion);

            var pins = new GroupBox { Text = "Arduino Mega pin assignments", Location = new Point(18, 410), Size = new Size(520, 350), ForeColor = Navy, Font = new Font("Segoe UI", 10F, FontStyle.Bold) };
            AddSetupInput(pins, 32, "X motor STEP pin", "X_STEP_PIN", 7M, 2M, 69M, 0, "pin");
            AddSetupInput(pins, 74, "X motor DIR pin", "X_DIR_PIN", 6M, 2M, 69M, 0, "pin");
            AddSetupInput(pins, 116, "Y motor STEP pin", "Y_STEP_PIN", 5M, 2M, 69M, 0, "pin");
            AddSetupInput(pins, 158, "Y motor DIR pin", "Y_DIR_PIN", 4M, 2M, 69M, 0, "pin");
            AddSetupInput(pins, 200, "X limit-switch pin", "X_HOME_PIN", 27M, 2M, 69M, 0, "pin");
            AddSetupInput(pins, 242, "Y limit-switch pin", "Y_HOME_PIN", 23M, 2M, 69M, 0, "pin");
            AddSetupInput(pins, 284, "Joystick push-button pin", "JOY_SW_PIN", 13M, 2M, 69M, 0, "pin");
            pins.Controls.Add(new Label { Text = "Pins must be unique. Pins 50–53 are reserved for Pixy2 SPI; 65–66 are joystick axes.", ForeColor = Color.Firebrick, AutoSize = true, Location = new Point(16, 320), Font = new Font("Segoe UI", 8.5F) });
            page.Controls.Add(pins);

            var actions = new Panel { Location = new Point(18, 780), Size = new Size(520, 100), BackColor = Color.White, BorderStyle = BorderStyle.FixedSingle };
            var reload = StyledButton("Reload from code", Color.White, Navy, 145);
            reload.FlatAppearance.BorderColor = Line;
            reload.Location = new Point(14, 16);
            reload.Click += delegate { LoadSetupFromEditor(); };
            var apply = StyledButton("Apply to editor", PaleTeal, Color.FromArgb(11, 93, 95), 145);
            apply.Location = new Point(171, 16);
            apply.Click += delegate { ApplySetupToEditor(false); };
            var applySave = StyledButton("Apply + save code", Teal, Color.White, 170);
            applySave.Location = new Point(328, 16);
            applySave.Click += delegate { ApplySetupToEditor(true); };
            actions.Controls.Add(reload);
            actions.Controls.Add(apply);
            actions.Controls.Add(applySave);
            actions.Controls.Add(new Label { Text = "Driver switches must match the pulse/revolution values entered above.", ForeColor = Color.Firebrick, AutoSize = true, Location = new Point(15, 63) });
            page.Controls.Add(actions);

            foreach (NumericUpDown input in setupInputs.Values) input.ValueChanged += delegate { UpdateStepResults(); };
            UpdateStepResults();
            return page;
        }

        private void AddSetupInput(Control parent, int top, string label, string constantName, decimal value, decimal minimum, decimal maximum, int decimals, string units)
        {
            var nameLabel = new Label { Text = label, AutoSize = true, ForeColor = Color.FromArgb(70, 88, 96), Font = new Font("Segoe UI", 9F), Location = new Point(16, top + 6) };
            var input = new ScrollFriendlyNumericUpDown
            {
                Name = constantName,
                Minimum = minimum,
                Maximum = maximum,
                Value = value,
                DecimalPlaces = decimals,
                Increment = decimals == 0 ? 100M : (decimals == 3 ? 0.1M : 0.5M),
                ThousandsSeparator = true,
                Location = new Point(265, top),
                Size = new Size(130, 28),
                Font = new Font("Segoe UI", 10F, FontStyle.Bold)
            };
            var unitLabel = new Label { Text = units, AutoSize = true, ForeColor = Color.DimGray, Location = new Point(404, top + 6) };
            parent.Controls.Add(nameLabel);
            parent.Controls.Add(input);
            parent.Controls.Add(unitLabel);
            setupInputs[constantName] = input;
        }

        private TabPage BuildGitTab()
        {
            var page = new TabPage("Versions + GitHub") { BackColor = Paper, Padding = new Padding(18), AutoScroll = true, AutoScrollMinSize = new Size(1120, 765) };
            page.Controls.Add(new Label { Text = "VERSION HISTORY & GITHUB", ForeColor = Navy, Font = new Font("Segoe UI", 16F, FontStyle.Bold), AutoSize = true, Location = new Point(18, 16) });
            page.Controls.Add(new Label { Text = "Save versions locally with Git, then push them to a GitHub repository. Passwords and tokens are never stored in this app.", ForeColor = Color.DimGray, AutoSize = true, Location = new Point(20, 49) });

            var connection = new GroupBox { Text = "Repository connection", Location = new Point(18, 84), Size = new Size(1060, 230), ForeColor = Navy, Font = new Font("Segoe UI", 10F, FontStyle.Bold) };
            connection.Controls.Add(new Label { Text = "Local project folder", AutoSize = true, ForeColor = Color.DimGray, Location = new Point(18, 34) });
            gitFolderBox = new TextBox { Text = appDirectory.TrimEnd(Path.DirectorySeparatorChar), Location = new Point(175, 30), Size = new Size(705, 27) };
            var browse = StyledButton("Browse", Color.White, Navy, 120);
            browse.FlatAppearance.BorderColor = Line;
            browse.Location = new Point(895, 27);
            browse.Click += delegate { BrowseGitFolder(); };
            connection.Controls.Add(gitFolderBox);
            connection.Controls.Add(browse);

            connection.Controls.Add(new Label { Text = "GitHub repository URL", AutoSize = true, ForeColor = Color.DimGray, Location = new Point(18, 78) });
            gitRemoteBox = new TextBox { Location = new Point(175, 74), Size = new Size(705, 27), Text = "https://github.com/your-name/wound-gantry.git" };
            var githubNew = StyledButton("Create on GitHub", PaleTeal, Color.FromArgb(11, 93, 95), 120);
            githubNew.Location = new Point(895, 71);
            githubNew.Click += delegate { Process.Start(new ProcessStartInfo { FileName = "https://github.com/new", UseShellExecute = true }); };
            connection.Controls.Add(gitRemoteBox);
            connection.Controls.Add(githubNew);

            connection.Controls.Add(new Label { Text = "Git display name", AutoSize = true, ForeColor = Color.DimGray, Location = new Point(18, 123) });
            gitNameBox = new TextBox { Location = new Point(175, 119), Size = new Size(270, 27) };
            connection.Controls.Add(gitNameBox);
            connection.Controls.Add(new Label { Text = "Git email", AutoSize = true, ForeColor = Color.DimGray, Location = new Point(480, 123) });
            gitEmailBox = new TextBox { Location = new Point(550, 119), Size = new Size(330, 27) };
            connection.Controls.Add(gitEmailBox);

            connection.Controls.Add(new Label { Text = "Version message", AutoSize = true, ForeColor = Color.DimGray, Location = new Point(18, 167) });
            gitCommitBox = new TextBox { Location = new Point(175, 163), Size = new Size(705, 27), Text = "Update gantry calibration and controls" };
            connection.Controls.Add(gitCommitBox);
            page.Controls.Add(connection);

            gitInitializeButton = StyledButton("1. Initialize repository", Color.White, Navy, 175);
            gitInitializeButton.FlatAppearance.BorderColor = Line;
            gitInitializeButton.Location = new Point(18, 334);
            gitInitializeButton.Click += async delegate { await InitializeGitRepository(); };
            gitCommitButton = StyledButton("2. Save version", Teal, Color.White, 150);
            gitCommitButton.Location = new Point(207, 334);
            gitCommitButton.Click += async delegate { await CommitGitVersion(); };
            gitPushButton = StyledButton("3. Push to GitHub", Orange, Color.White, 165);
            gitPushButton.Location = new Point(371, 334);
            gitPushButton.Click += async delegate { await PushGitVersion(); };
            page.Controls.Add(gitInitializeButton);
            page.Controls.Add(gitCommitButton);
            page.Controls.Add(gitPushButton);

            var security = new Label { Text = "GitHub may open a secure browser sign-in the first time you push.", ForeColor = Color.FromArgb(99, 119, 128), AutoSize = true, Location = new Point(556, 344) };
            page.Controls.Add(security);

            gitOutput = new TextBox { Location = new Point(18, 388), Size = new Size(1060, 330), Multiline = true, ReadOnly = true, ScrollBars = ScrollBars.Both, WordWrap = false, BackColor = Navy, ForeColor = Color.FromArgb(190, 230, 226), Font = new Font("Consolas", 9F), Anchor = AnchorStyles.Top | AnchorStyles.Left };
            page.Controls.Add(gitOutput);
            if (string.IsNullOrEmpty(gitPath)) gitOutput.Text = "Git was not found. Install Git for Windows before using this tab.";
            else gitOutput.Text = "Ready. Create an empty repository on GitHub, paste its URL above, then follow steps 1–3.";
            return page;
        }

        private Button StyledButton(string text, Color background, Color foreground, int width)
        {
            var button = new Button
            {
                Text = text,
                Width = width,
                Height = 34,
                BackColor = background,
                ForeColor = foreground,
                FlatStyle = FlatStyle.Flat,
                Cursor = Cursors.Hand,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold)
            };
            button.FlatAppearance.BorderColor = background == Color.White ? Line : background;
            return button;
        }

        private Button PhysicalJogButton(string text, string command, int left, int top)
        {
            var button = new Button
            {
                Text = text,
                Location = new Point(left, top),
                Size = new Size(80, 54),
                BackColor = Color.White,
                ForeColor = Navy,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Segoe UI Semibold", 10F, FontStyle.Bold),
                Cursor = Cursors.Hand,
                Enabled = false
            };
            button.FlatAppearance.BorderColor = Teal;
            button.FlatAppearance.BorderSize = 2;
            button.Click += delegate { SendCommand(command); };
            jogButtons.Add(button);
            return button;
        }

        private void UpdateStepResults()
        {
            if (xStepsResult == null || yStepsResult == null) return;
            decimal xLead = setupInputs["LEAD_MM_PER_REV_X"].Value;
            decimal yLead = setupInputs["LEAD_MM_PER_REV_Y"].Value;
            decimal xPulses = setupInputs["DRIVER_PULSES_PER_REV_X"].Value;
            decimal yPulses = setupInputs["DRIVER_PULSES_PER_REV_Y"].Value;
            xStepsResult.Text = "X: " + (xPulses / xLead).ToString("0.###", CultureInfo.InvariantCulture) + " steps/mm";
            yStepsResult.Text = "Y: " + (yPulses / yLead).ToString("0.###", CultureInfo.InvariantCulture) + " steps/mm";
        }

        private void LoadSetupFromEditor()
        {
            if (codeEditor == null || string.IsNullOrWhiteSpace(codeEditor.Text)) return;
            int loaded = 0;
            foreach (KeyValuePair<string, NumericUpDown> item in setupInputs)
            {
                decimal value;
                if (TryReadConstant(codeEditor.Text, item.Key, out value))
                {
                    value = Math.Max(item.Value.Minimum, Math.Min(item.Value.Maximum, value));
                    item.Value.Value = value;
                    loaded++;
                }
            }
            UpdateStepResults();
            SetFooter("Loaded " + loaded + " calibration and speed values from the Arduino editor.");
        }

        private void ApplySetupToEditor(bool saveAfterApply)
        {
            if (codeEditor == null || string.IsNullOrWhiteSpace(codeEditor.Text))
            {
                MessageBox.Show("Open an Arduino sketch first.", "No Arduino code", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            if (!ValidatePinAssignments()) return;
            string updated = codeEditor.Text;
            var missing = new List<string>();
            foreach (KeyValuePair<string, NumericUpDown> item in setupInputs)
            {
                bool changed;
                bool isPin = item.Key.EndsWith("_PIN", StringComparison.Ordinal);
                updated = ReplaceConstant(updated, item.Key, item.Value.Value, isPin, out changed);
                if (!changed) missing.Add(item.Key);
            }
            codeEditor.Text = updated;
            UpdateStepResults();
            if (missing.Count > 0)
            {
                MessageBox.Show("These settings were not found in the currently loaded sketch:\r\n\r\n" + string.Join("\r\n", missing.ToArray()), "Some settings were not applied", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            if (saveAfterApply) SaveSketch();
            tabs.SelectedIndex = 3;
            SetFooter(saveAfterApply ? "Calibration and speeds applied and saved. Compile before uploading." : "Calibration and speeds applied to the editor. Review and save when ready.");
        }

        private bool ValidatePinAssignments()
        {
            string[] pinNames = { "X_STEP_PIN", "X_DIR_PIN", "Y_STEP_PIN", "Y_DIR_PIN", "X_HOME_PIN", "Y_HOME_PIN", "JOY_SW_PIN" };
            var used = new Dictionary<int, string>();
            foreach (string name in pinNames)
            {
                int pin = Decimal.ToInt32(setupInputs[name].Value);
                if ((pin >= 50 && pin <= 53) || pin == 65 || pin == 66)
                {
                    MessageBox.Show("Pin " + pin + " cannot be assigned to " + name + ".\r\n\r\nPins 50–53 are used by Pixy2 SPI, and pins 65–66 are used by the joystick axes.", "Reserved Arduino pin", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return false;
                }
                string existing;
                if (used.TryGetValue(pin, out existing))
                {
                    MessageBox.Show(existing + " and " + name + " are both assigned to pin " + pin + ". Each assignment must use a different pin.", "Duplicate Arduino pin", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return false;
                }
                used[pin] = name;
            }
            return true;
        }

        private void LoadPixySignatureMappingFromEditor()
        {
            if (codeEditor == null || woundSignatureInput == null || markerSignatureInput == null) return;
            decimal value;
            if (TryReadConstant(codeEditor.Text, "WOUND_SIGNATURE", out value))
                woundSignatureInput.Value = Math.Max(woundSignatureInput.Minimum, Math.Min(woundSignatureInput.Maximum, value));
            if (TryReadConstant(codeEditor.Text, "CAL_MARKER_SIGNATURE", out value))
                markerSignatureInput.Value = Math.Max(markerSignatureInput.Minimum, Math.Min(markerSignatureInput.Maximum, value));
        }

        private void SavePixySignatureMapping()
        {
            if (codeEditor == null || string.IsNullOrWhiteSpace(codeEditor.Text))
            {
                MessageBox.Show("Open an Arduino sketch first.", "No Arduino code", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            if (woundSignatureInput.Value == markerSignatureInput.Value)
            {
                MessageBox.Show("The wound and calibration marker must use different Pixy2 signatures.", "Choose different signatures", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            bool woundChanged;
            bool markerChanged;
            string updated = ReplaceConstant(codeEditor.Text, "WOUND_SIGNATURE", woundSignatureInput.Value, true, out woundChanged);
            updated = ReplaceConstant(updated, "CAL_MARKER_SIGNATURE", markerSignatureInput.Value, true, out markerChanged);
            if (!woundChanged || !markerChanged)
            {
                MessageBox.Show("The Pixy2 signature constants were not found in the loaded Arduino sketch.", "Mapping not saved", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            codeEditor.Text = updated;
            if (SaveSketch()) SetFooter("Pixy2 signature mapping saved. Compile and upload the Arduino code to apply it.");
        }

        private static bool TryReadConstant(string source, string name, out decimal value)
        {
            Match match = Regex.Match(source, @"\b" + Regex.Escape(name) + @"\s*=\s*(-?\d+(?:\.\d+)?)f?", RegexOptions.CultureInvariant);
            if (!match.Success)
            {
                value = 0M;
                return false;
            }
            return decimal.TryParse(match.Groups[1].Value, NumberStyles.Float, CultureInfo.InvariantCulture, out value);
        }

        private static string ReplaceConstant(string source, string name, decimal value, bool integralLiteral, out bool changed)
        {
            var expression = new Regex(@"(\b" + Regex.Escape(name) + @"\s*=\s*)-?\d+(?:\.\d+)?f?", RegexOptions.CultureInvariant);
            changed = expression.IsMatch(source);
            if (!changed) return source;
            string formatted = integralLiteral
                ? Decimal.ToInt32(value).ToString(CultureInfo.InvariantCulture)
                : value.ToString("0.###", CultureInfo.InvariantCulture) + "f";
            return expression.Replace(source, delegate(Match match) { return match.Groups[1].Value + formatted; }, 1);
        }

        private static string FindGit()
        {
            string bundled = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), ".cache", "codex-runtimes", "codex-primary-runtime", "dependencies", "native", "git", "cmd", "git.exe");
            if (File.Exists(bundled)) return bundled;
            string programFiles = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), "Git", "cmd", "git.exe");
            if (File.Exists(programFiles)) return programFiles;
            string programFilesX86 = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Git", "cmd", "git.exe");
            return File.Exists(programFilesX86) ? programFilesX86 : null;
        }

        private void BrowseGitFolder()
        {
            using (var dialog = new FolderBrowserDialog())
            {
                dialog.Description = "Choose the folder whose files should be versioned.";
                dialog.SelectedPath = Directory.Exists(gitFolderBox.Text) ? gitFolderBox.Text : appDirectory;
                if (dialog.ShowDialog(this) == DialogResult.OK) gitFolderBox.Text = dialog.SelectedPath;
            }
        }

        private async Task InitializeGitRepository()
        {
            string folder = ValidateGitFolder(false);
            if (folder == null) return;
            if (string.IsNullOrEmpty(gitPath))
            {
                MessageBox.Show("Git for Windows was not found.", "Git missing", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            var commands = new List<string>();
            if (!Directory.Exists(Path.Combine(folder, ".git"))) commands.Add("init -b main");
            if (!string.IsNullOrWhiteSpace(gitNameBox.Text)) commands.Add("config user.name " + Quote(gitNameBox.Text.Trim()));
            if (!string.IsNullOrWhiteSpace(gitEmailBox.Text)) commands.Add("config user.email " + Quote(gitEmailBox.Text.Trim()));
            commands.Add("status --short");
            await RunGitCommands(folder, commands, "Repository initialized. Review the files, then save a version.");
        }

        private async Task CommitGitVersion()
        {
            string folder = ValidateGitFolder(true);
            if (folder == null) return;
            if (string.IsNullOrWhiteSpace(gitNameBox.Text) || string.IsNullOrWhiteSpace(gitEmailBox.Text))
            {
                MessageBox.Show("Enter your Git display name and email before saving a version.", "Git identity required", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            SaveSketch();
            var commands = new List<string>
            {
                "config user.name " + Quote(gitNameBox.Text.Trim()),
                "config user.email " + Quote(gitEmailBox.Text.Trim()),
                "add -A",
                "commit -m " + Quote(string.IsNullOrWhiteSpace(gitCommitBox.Text) ? "Update wound gantry project" : gitCommitBox.Text.Trim()),
                "status --short"
            };
            await RunGitCommands(folder, commands, "Version saved locally.");
        }

        private async Task PushGitVersion()
        {
            string folder = ValidateGitFolder(true);
            if (folder == null) return;
            string remote = gitRemoteBox.Text.Trim();
            if (!remote.StartsWith("https://github.com/", StringComparison.OrdinalIgnoreCase) || !remote.EndsWith(".git", StringComparison.OrdinalIgnoreCase))
            {
                MessageBox.Show("Paste the HTTPS GitHub repository URL, ending in .git.", "GitHub URL required", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            gitOutput.Clear();
            SetGitButtons(false);
            string existing = await RunGitCommand(folder, "remote get-url origin");
            string remoteCommand = existing.IndexOf("EXIT 0", StringComparison.OrdinalIgnoreCase) >= 0
                ? "remote set-url origin " + Quote(remote)
                : "remote add origin " + Quote(remote);
            var commands = new List<string> { remoteCommand, "branch -M main", "push -u origin main" };
            await RunGitCommands(folder, commands, "Push finished. Review the output for the GitHub result.");
        }

        private string ValidateGitFolder(bool requireRepository)
        {
            string folder = gitFolderBox.Text.Trim();
            if (!Directory.Exists(folder))
            {
                MessageBox.Show("Choose an existing local project folder.", "Folder not found", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return null;
            }
            if (requireRepository && !Directory.Exists(Path.Combine(folder, ".git")))
            {
                MessageBox.Show("Click Initialize repository first. This app uses a dedicated repository inside the selected folder.", "Repository not initialized", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return null;
            }
            return folder;
        }

        private async Task RunGitCommands(string folder, IList<string> commands, string completionMessage)
        {
            SetGitButtons(false);
            gitOutput.Clear();
            foreach (string command in commands)
            {
                string result = await RunGitCommand(folder, command);
                gitOutput.AppendText("> git " + command + "\r\n" + result + "\r\n");
                gitOutput.SelectionStart = gitOutput.TextLength;
                gitOutput.ScrollToCaret();
                if (result.IndexOf("EXIT 0", StringComparison.OrdinalIgnoreCase) < 0)
                {
                    SetFooter("Git stopped because a command failed. Review the output.");
                    SetGitButtons(true);
                    return;
                }
            }
            SetGitButtons(true);
            SetFooter(completionMessage);
        }

        private Task<string> RunGitCommand(string folder, string command)
        {
            return Task.Run<string>(delegate
            {
                try
                {
                    string safeFolder = folder.Replace('\\', '/');
                    var info = new ProcessStartInfo
                    {
                        FileName = gitPath,
                        Arguments = "-c safe.directory=" + Quote(safeFolder) + " " + command,
                        WorkingDirectory = folder,
                        UseShellExecute = false,
                        CreateNoWindow = false,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true
                    };
                    using (var process = Process.Start(info))
                    {
                        string standard = process.StandardOutput.ReadToEnd();
                        string error = process.StandardError.ReadToEnd();
                        process.WaitForExit();
                        return standard + error + "\r\nEXIT " + process.ExitCode;
                    }
                }
                catch (Exception ex)
                {
                    return ex.Message + "\r\nEXIT 1";
                }
            });
        }

        private void SetGitButtons(bool enabled)
        {
            if (gitInitializeButton != null) gitInitializeButton.Enabled = enabled;
            if (gitCommitButton != null) gitCommitButton.Enabled = enabled;
            if (gitPushButton != null) gitPushButton.Enabled = enabled;
        }

        private Button CommandButton(string key, string title, string description, int top)
        {
            var button = new Button
            {
                Text = key + "     " + title + "\r\n       " + description,
                TextAlign = ContentAlignment.MiddleLeft,
                Location = new Point(18, top),
                Size = new Size(314, 72),
                BackColor = Color.White,
                ForeColor = Navy,
                FlatStyle = FlatStyle.Flat,
                Font = new Font("Segoe UI", 9F, FontStyle.Bold),
                Cursor = Cursors.Hand
            };
            button.FlatAppearance.BorderColor = Line;
            return button;
        }

        private void RefreshPorts()
        {
            string selected = portList == null ? null : portList.SelectedItem as string;
            string[] ports = SerialPort.GetPortNames();
            Array.Sort(ports);
            portList.Items.Clear();
            portList.Items.AddRange(ports);
            if (selected != null && portList.Items.Contains(selected)) portList.SelectedItem = selected;
            else if (portList.Items.Count > 0) portList.SelectedIndex = 0;
            SetFooter(ports.Length == 0 ? "No Arduino COM port found." : "Select the Arduino COM port and connect.");
        }

        private void ToggleSerial()
        {
            if (serial != null && serial.IsOpen) DisconnectSerial(true);
            else ConnectSerial();
        }

        private void ConnectSerial()
        {
            if (portList.SelectedItem == null)
            {
                MessageBox.Show("Select the Arduino COM port first.", "No COM port", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            try
            {
                serial = new SerialPort(portList.SelectedItem.ToString(), 115200, Parity.None, 8, StopBits.One);
                serial.DtrEnable = false;
                serial.RtsEnable = false;
                serial.NewLine = "\n";
                serial.DataReceived += SerialDataReceived;
                serial.Open();
                connectButton.Text = "Disconnect";
                machineState.Text = "Connected · Home required";
                machineState.ForeColor = Color.DarkOrange;
                SetMotionButtons(true);
                SetJogButtons(false);
                AppendMachine("Connected to " + serial.PortName + " at 115200. Wait two seconds, then home.\r\n");
                SetFooter("Arduino connected. Machine position is not valid until homing completes.");
            }
            catch (Exception ex)
            {
                AppendArduinoError("Connection failed: " + ex.Message + "\r\n");
                MessageBox.Show("Could not open the Arduino port. Close Arduino Serial Monitor and try again.\r\n\r\n" + ex.Message, "Connection failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
                DisconnectSerial(false);
            }
        }

        private void DisconnectSerial(bool logMessage)
        {
            try
            {
                if (serial != null)
                {
                    serial.DataReceived -= SerialDataReceived;
                    if (serial.IsOpen) serial.Close();
                    serial.Dispose();
                }
            }
            catch { }
            serial = null;
            if (connectButton != null) connectButton.Text = "Connect";
            if (machineState != null)
            {
                machineState.Text = "Disconnected · Not homed";
                machineState.ForeColor = Color.Firebrick;
            }
            SetMotionButtons(false);
            if (logMessage) AppendMachine("Arduino disconnected.\r\n");
        }

        private void SerialDataReceived(object sender, SerialDataReceivedEventArgs e)
        {
            try
            {
                string text = serial.ReadExisting();
                BeginInvoke((Action)delegate
                {
                    string normalized = text.Replace("\n", "\r\n").Replace("\r\r\n", "\r\n");
                    AppendMachine(normalized);
                    CaptureArduinoErrors(normalized);
                    if (text.IndexOf("Homed.", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        machineState.Text = "Connected · Homed";
                        machineState.ForeColor = Color.DarkGreen;
                        SetJogButtons(true);
                        SetFooter("Machine homed. Motion coordinates are valid.");
                    }
                    if (text.IndexOf("FAULT", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        machineState.Text = "Connected · Faulted";
                        machineState.ForeColor = Color.Firebrick;
                        SetJogButtons(false);
                    }
                });
            }
            catch { }
        }

        private void AppendMachine(string message)
        {
            // Main Control intentionally displays errors only.
            Debug.WriteLine(message);
        }

        private void CaptureArduinoErrors(string message)
        {
            string[] lines = message.Replace("\r", "").Split('\n');
            foreach (string line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;
                if (line.IndexOf("ERROR", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    line.IndexOf("FAULT", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    line.IndexOf("ALARM", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    line.IndexOf("TIMEOUT", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    line.IndexOf("FAILED", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    line.IndexOf("REJECTED", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    AppendArduinoError(line.Trim() + "\r\n");
                }
            }
        }

        private void AppendArduinoError(string message)
        {
            if (arduinoErrorLog == null) return;
            arduinoErrorLog.AppendText(DateTime.Now.ToString("HH:mm:ss") + "  " + message);
            arduinoErrorLog.SelectionStart = arduinoErrorLog.TextLength;
            arduinoErrorLog.ScrollToCaret();
        }

        private void SendCommand(string command)
        {
            if (serial == null || !serial.IsOpen)
            {
                MessageBox.Show("Connect to the Arduino first.", "Arduino disconnected", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }
            try
            {
                serial.Write(command + "\n");
                AppendMachine("Sent: " + command + "\r\n");
                if (command == "H" || command == "C")
                {
                    machineState.Text = "Connected · Motion running";
                    machineState.ForeColor = Color.DarkOrange;
                    SetJogButtons(false);
                }
            }
            catch (Exception ex)
            {
                AppendArduinoError("Serial command failed: " + ex.Message + "\r\n");
                MessageBox.Show(ex.Message, "Serial command failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
                DisconnectSerial(false);
            }
        }

        private void ConfirmCorners()
        {
            DialogResult result = MessageBox.Show(
                "This will home the gantry and move near all four edges of the configured 12 × 8 inch workspace.\r\n\r\nConfirm both axes have clear, safe travel.",
                "Confirm four-corner test",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Warning);
            if (result == DialogResult.Yes) SendCommand("C");
        }

        private void SetMotionButtons(bool enabled)
        {
            if (homeButton != null) homeButton.Enabled = enabled;
            if (cornersButton != null) cornersButton.Enabled = enabled;
            if (statusButton != null) statusButton.Enabled = enabled;
            if (!enabled) SetJogButtons(false);
        }

        private void SetJogButtons(bool enabled)
        {
            foreach (Button button in jogButtons) button.Enabled = enabled;
        }

        private void MainFormKeyDown(object sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.F6)
            {
                ShowCodeEditor();
                e.SuppressKeyPress = true;
                return;
            }
            if (tabs.SelectedIndex != 0 || serial == null || !serial.IsOpen) return;
            if (e.KeyCode == Keys.H)
            {
                SendCommand("H");
                e.SuppressKeyPress = true;
            }
            else if (e.KeyCode == Keys.C)
            {
                ConfirmCorners();
                e.SuppressKeyPress = true;
            }
        }

        private void ShowCodeEditor()
        {
            foreach (TabPage page in tabs.TabPages)
            {
                if (page.Text.StartsWith("Arduino Code", StringComparison.Ordinal))
                {
                    tabs.SelectedTab = page;
                    if (codeEditor != null) codeEditor.Focus();
                    SetFooter("Arduino code editor opened. Edit the sketch, then Save and Compile.");
                    return;
                }
            }
        }

        private void LoadSketch(string path)
        {
            try
            {
                if (!File.Exists(path))
                {
                    codeEditor.Text = "// Open an Arduino .ino file to begin.\r\n";
                    codePathLabel.Text = "No sketch loaded";
                    return;
                }
                sketchPath = path;
                codeEditor.Text = File.ReadAllText(path);
                codePathLabel.Text = path;
                LoadSetupFromEditor();
                LoadPixySignatureMappingFromEditor();
                SetFooter("Loaded Arduino sketch: " + Path.GetFileName(path));
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Could not open sketch", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void OpenSketch()
        {
            using (var dialog = new OpenFileDialog())
            {
                dialog.Filter = "Arduino sketches (*.ino)|*.ino|All files (*.*)|*.*";
                dialog.InitialDirectory = File.Exists(sketchPath) ? Path.GetDirectoryName(sketchPath) : appDirectory;
                if (dialog.ShowDialog(this) == DialogResult.OK) LoadSketch(dialog.FileName);
            }
        }

        private bool SaveSketch()
        {
            try
            {
                if (string.IsNullOrWhiteSpace(sketchPath)) return false;
                File.WriteAllText(sketchPath, codeEditor.Text, new UTF8Encoding(false));
                codePathLabel.Text = sketchPath;
                SetFooter("Saved " + Path.GetFileName(sketchPath));
                return true;
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Could not save sketch", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }

        private async Task RunArduinoCli(bool upload)
        {
            if (buildBusy) return;
            if (!File.Exists(arduinoCliPath))
            {
                MessageBox.Show("Arduino CLI was not found. Install or repair Arduino IDE 2.", "Arduino tools missing", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }
            if (!SaveSketch()) return;

            string uploadPort = portList.SelectedItem == null ? null : portList.SelectedItem.ToString();
            if (upload && string.IsNullOrEmpty(uploadPort))
            {
                MessageBox.Show("Select the Arduino COM port before uploading.", "No COM port", MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            if (upload)
            {
                DialogResult confirm = MessageBox.Show(
                    "Uploading resets the Arduino and erases the current homed position.\r\n\r\nEnsure the gantry is stationary and the plasma source is disabled. Continue?",
                    "Confirm firmware upload",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Warning);
                if (confirm != DialogResult.Yes) return;
                DisconnectSerial(false);
            }

            buildBusy = true;
            compileButton.Enabled = false;
            uploadButton.Enabled = false;
            buildOutput.Clear();
            buildOutput.AppendText(upload ? "Compiling and uploading...\r\n\r\n" : "Compiling...\r\n\r\n");
            SetFooter(upload ? "Compiling and uploading firmware..." : "Compiling firmware...");

            string output = await Task.Run<string>(delegate
            {
                try
                {
                    string sketchName = Path.GetFileNameWithoutExtension(sketchPath);
                    string stagingRoot = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "WoundGantryStudio", "SketchBuild", sketchName);
                    Directory.CreateDirectory(stagingRoot);
                    string stagedSketch = Path.Combine(stagingRoot, sketchName + ".ino");
                    File.Copy(sketchPath, stagedSketch, true);

                    string arguments = "compile --fqbn arduino:avr:mega ";
                    if (upload) arguments += "--upload --port " + Quote(uploadPort) + " ";
                    arguments += Quote(stagingRoot);

                    var info = new ProcessStartInfo
                    {
                        FileName = arduinoCliPath,
                        Arguments = arguments,
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        RedirectStandardOutput = true,
                        RedirectStandardError = true,
                        WorkingDirectory = stagingRoot
                    };
                    var collected = new StringBuilder();
                    using (var process = new Process())
                    {
                        process.StartInfo = info;
                        process.OutputDataReceived += delegate(object s, DataReceivedEventArgs e) { if (e.Data != null) lock (collected) collected.AppendLine(e.Data); };
                        process.ErrorDataReceived += delegate(object s, DataReceivedEventArgs e) { if (e.Data != null) lock (collected) collected.AppendLine(e.Data); };
                        process.Start();
                        process.BeginOutputReadLine();
                        process.BeginErrorReadLine();
                        process.WaitForExit();
                        lock (collected) collected.AppendLine("\r\nExit code: " + process.ExitCode);
                    }
                    return collected.ToString();
                }
                catch (Exception ex)
                {
                    return "Application error: " + ex.Message;
                }
            });

            buildOutput.Text = output;
            buildOutput.SelectionStart = buildOutput.TextLength;
            buildOutput.ScrollToCaret();
            buildBusy = false;
            compileButton.Enabled = true;
            uploadButton.Enabled = true;
            bool buildPassed = output.IndexOf("Exit code: 0", StringComparison.OrdinalIgnoreCase) >= 0;
            if (!buildPassed)
            {
                string errorSummary = output.Length > 4000 ? output.Substring(output.Length - 4000) : output;
                AppendArduinoError((upload ? "Compile/upload failed:" : "Compilation failed:") + "\r\n" + errorSummary + "\r\n");
                SetFooter(upload ? "Compile/upload failed. Review Main Control errors or compiler messages." : "Compilation failed. Review Main Control errors or compiler messages.");
            }
            else if (upload)
            {
                machineState.Text = "Disconnected · Home required after upload";
                machineState.ForeColor = Color.Firebrick;
                SetFooter("Upload finished. Reconnect to the Arduino and home the machine before movement.");
            }
            else SetFooter("Compilation passed.");
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private void SwitchPixyHost(Panel target)
        {
            if (target == null) return;
            pixyHost = target;
            if (pixyWindow != IntPtr.Zero)
            {
                SetParent(pixyWindow, pixyHost.Handle);
                ResizeDockedPixy();
            }
        }

        private void StartOrAttachPixy()
        {
            pixyStandaloneRequested = false;
            if (pixyWindow != IntPtr.Zero)
            {
                ResizeDockedPixy();
                return;
            }
            try
            {
                Process[] running = Process.GetProcessesByName("PixyMon");
                if (running.Length > 0)
                {
                    pixyProcess = running[0];
                    startedPixy = false;
                }
                else
                {
                    if (!File.Exists(pixyMonPath))
                    {
                        MessageBox.Show("PixyMon was not found at:\r\n" + pixyMonPath, "PixyMon missing", MessageBoxButtons.OK, MessageBoxIcon.Error);
                        return;
                    }
                    pixyProcess = Process.Start(new ProcessStartInfo { FileName = pixyMonPath, UseShellExecute = true });
                    startedPixy = true;
                }
                dockAttempts = 0;
                pixyStatus.Text = "● Starting PixyMon...";
                pixyStatus.ForeColor = Color.DarkOrange;
                if (pixyTimer == null)
                {
                    pixyTimer = new System.Windows.Forms.Timer();
                    pixyTimer.Interval = 250;
                    pixyTimer.Tick += TryDockPixy;
                }
                pixyTimer.Start();
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Could not start PixyMon", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void OpenPixyStandalone()
        {
            try
            {
                pixyStandaloneRequested = true;
                if (pixyTimer != null) pixyTimer.Stop();

                if (pixyWindow != IntPtr.Zero)
                {
                    SetParent(pixyWindow, IntPtr.Zero);
                    SetWindowLong(pixyWindow, GwlStyle, pixyOriginalStyle);
                    ShowWindow(pixyWindow, SwRestore);
                    pixyWindow = IntPtr.Zero;
                    pixyStatus.Text = "● PixyMon open in its own window";
                    pixyStatus.ForeColor = Color.DarkGreen;
                    startPixyButton.Text = "Attach camera here";
                    startPixyButton.Enabled = true;
                    return;
                }

                if (!File.Exists(pixyMonPath))
                {
                    MessageBox.Show("PixyMon was not found at:\r\n" + pixyMonPath, "PixyMon missing", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }

                pixyProcess = Process.Start(new ProcessStartInfo { FileName = pixyMonPath, UseShellExecute = true });
                startedPixy = true;
                dockAttempts = 0;
                pixyStatus.Text = "● Opening PixyMon window...";
                pixyStatus.ForeColor = Color.DarkOrange;
                if (pixyTimer == null)
                {
                    pixyTimer = new System.Windows.Forms.Timer();
                    pixyTimer.Interval = 250;
                    pixyTimer.Tick += TryDockPixy;
                }
                pixyTimer.Start();
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message, "Could not open PixyMon", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void TryDockPixy(object sender, EventArgs e)
        {
            dockAttempts++;
            try
            {
                if (pixyProcess == null || pixyProcess.HasExited)
                {
                    pixyTimer.Stop();
                    pixyStatus.Text = "PixyMon closed";
                    pixyWindow = IntPtr.Zero;
                    return;
                }
                pixyProcess.Refresh();
                IntPtr handle = pixyProcess.MainWindowHandle;
                if (handle == IntPtr.Zero)
                {
                    if (dockAttempts > 80)
                    {
                        pixyTimer.Stop();
                        pixyStatus.Text = "PixyMon opened separately";
                    }
                    return;
                }

                pixyWindow = handle;
                pixyOriginalStyle = GetWindowLong(handle, GwlStyle);
                if (pixyStandaloneRequested)
                {
                    ShowWindow(handle, SwRestore);
                    pixyTimer.Stop();
                    pixyWindow = IntPtr.Zero;
                    pixyStatus.Text = "● PixyMon open in its own window";
                    pixyStatus.ForeColor = Color.DarkGreen;
                    startPixyButton.Text = "Attach camera here";
                    startPixyButton.Enabled = true;
                    SetFooter("PixyMon opened separately. Return to the app when camera setup is complete.");
                    return;
                }
                SetParent(handle, pixyHost.Handle);
                int dockedStyle = (pixyOriginalStyle & ~WsCaption & ~WsThickFrame) | WsChild | WsVisible;
                SetWindowLong(handle, GwlStyle, dockedStyle);
                ShowWindow(handle, SwRestore);
                ResizeDockedPixy();
                pixyTimer.Stop();
                pixyStatus.Text = "● Pixy2 USB view attached";
                pixyStatus.ForeColor = Color.DarkGreen;
                startPixyButton.Text = "PixyMon attached";
                startPixyButton.Enabled = false;
                SetFooter("PixyMon attached. Use its gear button to change Pixy2 settings.");
            }
            catch
            {
                if (dockAttempts > 80) pixyTimer.Stop();
            }
        }

        private void ResizeDockedPixy()
        {
            if (pixyWindow != IntPtr.Zero && pixyHost != null)
                MoveWindow(pixyWindow, 0, 0, Math.Max(1, pixyHost.ClientSize.Width), Math.Max(1, pixyHost.ClientSize.Height), true);
        }

        private void SetFooter(string text)
        {
            if (footerStatus != null) footerStatus.Text = text;
        }

        private void MainFormClosing(object sender, FormClosingEventArgs e)
        {
            DisconnectSerial(false);
            if (pixyTimer != null) pixyTimer.Stop();
            try
            {
                if (pixyProcess != null && !pixyProcess.HasExited)
                {
                    if (startedPixy)
                    {
                        pixyProcess.CloseMainWindow();
                        if (!pixyProcess.WaitForExit(750)) pixyProcess.Kill();
                    }
                    else if (pixyWindow != IntPtr.Zero)
                    {
                        SetParent(pixyWindow, IntPtr.Zero);
                        SetWindowLong(pixyWindow, GwlStyle, pixyOriginalStyle);
                        ShowWindow(pixyWindow, SwRestore);
                    }
                }
            }
            catch { }
        }
    }
}
