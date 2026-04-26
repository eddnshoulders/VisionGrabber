# ── Configuration ─────────────────────────────────────────────────────────────

# Flask
FLASK_URL         = "http://localhost:5000"
FLASK_PORT        = 5000
FLASK_DEBUG       = False

# IPC
IPC_SOCKET_PATH   = "/tmp/visiongrabber.sock"
IPC_TIMEOUT       = 120.00

# Heartbeat
HEARTBEAT_INTERVAL    = 2.0
HEARTBEAT_MAX_FAILURES = 3

# Button controller
BUTTON_PORT       = "/dev/ttyButton"
BUTTON_BAUDRATE   = 115200

# Machine UART
MACHINE_UART      = "/dev/ttyAMA0"
MACHINE_BAUDRATE  = 115200

# Feedrates
SCAN_FEEDRATE     = 1500
MOVE_FEEDRATE     = 10000
BED_FEEDRATE      = 3000

# Scan area
SCAN_Y_STEP       = 15
SCAN_X_START      = 120
SCAN_X_END        = 0
SCAN_Y_START      = 120
SCAN_Y_END        = 0

STEP_SETTLE_TIME  = 0.1

# Z positions
Z_BED_DOWN        = 40
Z_BED_UP          = 5

# Gripper
GRIPPER_OPEN      = 23
GRIPPER_CLOSE     = 128

# Drop position
DROP_X            = 20
DROP_Y            = 0

# Vision alignment
PICKUP_CX         = 308
PICKUP_CY         = 220
IMAGE_CX          = 320
IMAGE_CY          = 240
SCALE_X           = -12
SCALE_Y           = 12

ALIGN_THRESH_X    = 2
ALIGN_THRESH_Y    = 2

# Detection
N_FRAMES          = 2
Y_DETECTIONS      = 1
DET_STEPBACK      = 2

# Fine-tuning timeout
FINE_TUNE_TIMEOUT = 30.0
FINE_TUNE_MAX_ATTEMPTS = 10

# Camera indices
TOOLHEAD_CAMERA_INDEX = 0
OVERHEAD_CAMERA_INDEX = 1

# Presets directory (relative to backend/)
PRESETS_DIR       = "../presets"

# Calibration grid
CALIB_GRID_X           = 3      # points in X
CALIB_GRID_Y           = 3      # points in Y
CALIB_MARGIN_X_MIN     = 20.0   # mm from X minimum (SCAN_X_END)
CALIB_MARGIN_X_MAX     = 25.0   # mm from X maximum (SCAN_X_START)
CALIB_MARGIN_Y_MIN     = 60.0   # mm from Y minimum (SCAN_Y_END)
CALIB_MARGIN_Y_MAX     = 10.0   # mm from Y maximum (SCAN_Y_START)

# Grabber offset from toolhead circle centre (mm)
CALIB_GRABBER_OFFSET_X = 0.0
CALIB_GRABBER_OFFSET_Y = 0.0

# Calibration data file
CALIB_FILE             = "../presets/calibration.json"

# Parallax correction
CALIB_CAMERA_TO_TOOLHEAD  = 114.0   # mm, camera to calibration circle
CALIB_CAMERA_TO_BED_DOWN  = 236.0   # mm, camera to cylinder top at Z_BED_DOWN
