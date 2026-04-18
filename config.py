# ── Configuration ─────────────────────────────────────────────────────────────

KLIPPER_SOCK      = "/home/pi/printer_data/comms/klippy.sock"
FLASK_URL         = "http://localhost:5000"

BUTTON_PORT       = "/dev/ttyButton"
BUTTON_BAUDRATE   = 115200

SCAN_FEEDRATE     = 2500    # mm/min -- scan step moves
MOVE_FEEDRATE     = 8000    # mm/min -- repositioning moves
BED_FEEDRATE      = 3000    # mm/min -- Z moves

SCAN_X_STEP       = 15      # mm -- X increment between scan points
SCAN_Y_STEP       = 20      # mm -- Y increment between scan rows
SCAN_X_START      = 120     # mm
SCAN_X_END        = 0       # mm
SCAN_Y_START      = 120     # mm
SCAN_Y_END        = 0       # mm

STEP_SETTLE_TIME  = 0.2     # seconds to wait after each move before checking detection

Z_BED_DOWN        = 30      # mm -- bed lowered (safe scanning height)
Z_BED_UP          = 5       # mm -- bed raised (pick height)

GRIPPER_OPEN      = "SET_SERVO SERVO=Grabber angle=32"
GRIPPER_CLOSE     = "SET_SERVO SERVO=Grabber angle=145"

DROP_X            = 20      # mm -- drop position
DROP_Y            = 0       # mm

PICKUP_CX         = 307     # image X position of circle centre when aligned for pickup
PICKUP_CY         = 219     # image Y position of circle centre when aligned for pickup
IMAGE_CX          = 320     # pixels -- image centre X (half of frame width)
IMAGE_CY          = 240     # pixels -- image centre Y (half of frame height)
SCALE_X           = -4.3    # pixels per mm
SCALE_Y           = 4.3     # pixels per mm

ALIGN_THRESH_X    = 2       # pixels -- alignment tolerance in X
ALIGN_THRESH_Y    = 2       # pixels -- alignment tolerance in Y

N_FRAMES          = 5       # number of frames to sample for confirmed detection
Y_DETECTIONS      = 3       # minimum positive detections required out of N_FRAMES
CONFIRM_TIMEOUT   = 3.0     # seconds to wait for N confirmed frames

DET_STEPBACK      = 6       # how far to step back after detection (reverse overshoot on stopping)