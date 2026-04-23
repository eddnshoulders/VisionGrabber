# ── Configuration ─────────────────────────────────────────────────────────────

FLASK_URL         = "http://localhost:5000"

BUTTON_PORT       = "/dev/ttyButton"
BUTTON_BAUDRATE   = 115200

MACHINE_UART      = "/dev/ttyAMA0"
MACHINE_BAUDRATE  = 115200

SCAN_FEEDRATE     = 1500
MOVE_FEEDRATE     = 10000
BED_FEEDRATE      = 3000

SCAN_Y_STEP       = 15
SCAN_X_START      = 120
SCAN_X_END        = 0
SCAN_Y_START      = 120
SCAN_Y_END        = 0

STEP_SETTLE_TIME  = 0.1

Z_BED_DOWN        = 40
Z_BED_UP          = 5

GRIPPER_OPEN      = "M280 S23"
GRIPPER_CLOSE     = "M280 S128"

DROP_X            = 20
DROP_Y            = 0

PICKUP_CX         = 308
PICKUP_CY         = 238
IMAGE_CX          = 320
IMAGE_CY          = 240
SCALE_X           = -12
SCALE_Y           = 12

ALIGN_THRESH_X    = 2
ALIGN_THRESH_Y    = 2

N_FRAMES          = 2
Y_DETECTIONS      = 1

DET_STEPBACK      = 2

