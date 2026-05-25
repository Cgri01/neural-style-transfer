import os
from pathlib import Path

from dotenv import load_dotenv

_backend_root = Path(__file__).resolve().parent.parent
load_dotenv(_backend_root / ".env")

MODELS_DIR = os.getenv("MODELS_DIR", "models")


STYLE_PROCESSING = {
    "starry_night": {
        "architecture": "starry_night",
        "norm_mode": "half",
        "output_mode": "tanh",
        "recommended_size": 512,
    },
    "candy": {
        "architecture": "fast_style",
        "norm_mode": "raw255",
        "output_mode": "clamp",
        "recommended_size": 384,
    },
    "mosaic": {
        "architecture": "fast_style",
        "norm_mode": "raw255",
        "output_mode": "clamp",
        "recommended_size": 384,
    },
    "rain_princess": {
        "architecture": "fast_style",
        "norm_mode": "raw255",
        "output_mode": "clamp",
        "recommended_size": 384,
    },
    "udnie": {
        "architecture": "fast_style",
        "norm_mode": "raw255",
        "output_mode": "clamp",
        "recommended_size": 384,
    },
}

AVAILABLE_STYLES = {
    "starry_night": {
        "id": "starry_night",
        "name": "🌙 Van Gogh - Starry Night",
        "path": "models/Starry_Night_512.pth",
        "description": "Abstract coup attempts, navy blue and yellow posts.",
        "recommended_size": STYLE_PROCESSING["starry_night"]["recommended_size"],
        "is_available": True,
    },
    "udnie": {
        "id": "udnie",
        "name": "🎨 Udnie - Francis Picabia",
        "path": "models/udnie.pth",
        "description": "Abstract pastel tones, soft transitions.",
        "recommended_size": STYLE_PROCESSING["udnie"]["recommended_size"],
        "is_available": True,
    },
    "rain_princess": {
        "id": "rain_princess",
        "name": "🌧️ Rain Princess",
        "path": "models/rain_princess.pth",
        "description": "Dark and dramatic tones",
        "recommended_size": STYLE_PROCESSING["rain_princess"]["recommended_size"],
        "is_available": True,
    },
    "candy": {
        "id": "candy",
        "name": "🍬 Candy Style",
        "path": "models/candy.pth",
        "description": "Vibrant, cartoon-like colors",
        "recommended_size": STYLE_PROCESSING["candy"]["recommended_size"],
        "is_available": True,
    },
    "mosaic": {
        "id": "mosaic",
        "name": "🔲 Mosaic Style",
        "path": "models/mosaic.pth",
        "description": "Mosaic-like colored texture",
        "recommended_size": STYLE_PROCESSING["mosaic"]["recommended_size"],
        "is_available": True,
    },
}

DEFAULT_STYLE = "starry_night"
DEFAULT_PROCESS_SIZE = 384

_current_style = DEFAULT_STYLE
_current_model_path = AVAILABLE_STYLES[DEFAULT_STYLE]["path"]


def get_style_processing_config(style_id):
    if style_id not in STYLE_PROCESSING:
        raise ValueError(f"Style processing config could not find: {style_id}")
    return STYLE_PROCESSING[style_id]


def get_available_styles():
    return [
        {
            "id": style_id,
            "name": style["name"],
            "description": style["description"],
            "is_available": style["is_available"],
            "recommended_size": style["recommended_size"],
            "architecture": STYLE_PROCESSING[style_id]["architecture"],
        }
        for style_id, style in AVAILABLE_STYLES.items()
    ]


def get_current_style():
    return _current_style


def get_current_model_path():
    return _current_model_path


def set_current_style(style_id):
    global _current_style, _current_model_path
    if style_id not in AVAILABLE_STYLES:
        return False, f"Style bulunamadı: {style_id}"
    if not AVAILABLE_STYLES[style_id]["is_available"]:
        return False, f"Style henüz kullanılamaz: {style_id}"
    _current_style = style_id
    _current_model_path = AVAILABLE_STYLES[style_id]["path"]
    return True, None


def get_style_recommended_size(style_id):
    if style_id in AVAILABLE_STYLES:
        return AVAILABLE_STYLES[style_id]["recommended_size"]
    return DEFAULT_PROCESS_SIZE
