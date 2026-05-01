"""
Camera detection parameters for VisionGrabber.

Each camera has its own parameter set stored as JSON in the presets/
directory. Parameters can be updated live via the REST API and saved
as named presets.
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from camera.camera_thread import CameraId

from config import PRESETS_DIR

logger = logging.getLogger(__name__)

PRESETS_PATH = Path(__file__).parent.parent / PRESETS_DIR


@dataclass
class CameraParams:
    # Stream
    frame_width:  int   = 640
    frame_height: int   = 480
    jpeg_quality: int   = 65
    stream_fps:   int   = 10

    # Debug view
    debug_view: str = "annotated"   # raw|gray|mask|contours|annotated|tiled

    # Blur
    blur_kernel: int = 5

    # Threshold
    threshold_mode:       str = "adaptive"  # binary|inverse|hsv|adaptive
    threshold_value:      int = 110
    adaptive_block_size:  int = 60
    adaptive_c:           int = -10

    # HSV
    hsv_h1_lo: int = 0;   hsv_h1_hi: int = 10
    hsv_h2_lo: int = 160; hsv_h2_hi: int = 180
    hsv_s_lo:  int = 100; hsv_s_hi:  int = 255
    hsv_v_lo:  int = 50;  hsv_v_hi:  int = 255

    # Contour filtering
    min_area:        float = 45000.0
    max_area:        float = 150000.0
    circularity_min: float = 0.75
    min_radius:      int   = 120
    max_radius:      int   = 220

    # ROI
    roi_x_min: int = 0;   roi_x_max: int = 640
    roi_y_min: int = 0;   roi_y_max: int = 480

    # Visualisation
    show_all_contours:      bool = True
    show_accepted_contours: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    def update(self, key: str, value) -> bool:
        """Update a single parameter. Returns False if key unknown."""
        if not hasattr(self, key):
            return False
        current = getattr(self, key)
        if isinstance(current, bool):
            setattr(self, key, bool(value))
        elif isinstance(current, int):
            setattr(self, key, int(float(value)))
        elif isinstance(current, float):
            setattr(self, key, float(value))
        else:
            setattr(self, key, value)
        return True


def _default_filename(camera_id: "CameraId") -> Path:
    return PRESETS_PATH / f"{camera_id.name.lower()}_params.json"


def load_params(camera_id: "CameraId") -> CameraParams:
    """Load params from the camera's default JSON file, falling back to defaults."""
    path = _default_filename(camera_id)
    params = CameraParams()
    if path.exists():
        try:
            overrides = json.loads(path.read_text())
            for k, v in overrides.items():
                params.update(k, v)
            logger.info(f"[Params] Loaded {path}")
        except Exception as exc:
            logger.warning(f"[Params] Failed to load {path}: {exc}, using defaults")
    return params


def save_params(params: CameraParams, camera_id: "CameraId",
                name: str = None) -> Path:
    """
    Save params to a named preset file.
    If name is None, saves to the camera's default file.
    """
    PRESETS_PATH.mkdir(parents=True, exist_ok=True)
    if name:
        path = _preset_filename(camera_id, name)
    else:
        path = _default_filename(camera_id)
    path.write_text(json.dumps(params.to_dict(), indent=2))
    logger.info(f"[Params] Saved to {path}")
    return path


def _active_preset_file(camera_id: "CameraId") -> Path:
    return PRESETS_PATH / f"{camera_id.name.lower()}_active_preset.txt"


def get_active_preset(camera_id: "CameraId") -> str | None:
    """Return the name of the currently active (default) preset, or None."""
    path = _active_preset_file(camera_id)
    if path.exists():
        return path.read_text().strip() or None
    return None


def set_default_preset(camera_id: "CameraId", name: str) -> Path:
    """
    Set a named preset as the default:
    - Copies the preset to the default _params.json file
    - Records the preset name in the active preset sidecar file
    """
    preset_path = _preset_filename(camera_id, name)
    if not preset_path.exists():
        raise FileNotFoundError(f"Preset not found: {name}")

    # Copy preset to default file
    default_path = _default_filename(camera_id)
    default_path.write_text(preset_path.read_text())

    # Record active preset name
    _active_preset_file(camera_id).write_text(name)

    logger.info(f"[Params] Default set to preset '{name}' for {camera_id.name}")
    return default_path


def _preset_filename(camera_id: "CameraId", name: str) -> Path:
    """Full path for a named preset file."""
    return PRESETS_PATH / f"{camera_id.name.lower()}_{name}.json"


def _preset_name_from_file(camera_id: "CameraId", path: Path) -> str:
    """Extract preset name from filename by stripping camera prefix."""
    prefix = f"{camera_id.name.lower()}_"
    return path.stem[len(prefix):]


def list_presets(camera_id: "CameraId") -> list[str]:
    """List all saved preset names for this camera only."""
    if not PRESETS_PATH.exists():
        return []
    prefix  = f"{camera_id.name.lower()}_"
    exclude = {
        f"{camera_id.name.lower()}_params",
        f"{camera_id.name.lower()}_active_preset",
    }
    return sorted([
        _preset_name_from_file(camera_id, p)
        for p in PRESETS_PATH.glob(f"{prefix}*.json")
        if p.stem not in exclude
    ])
