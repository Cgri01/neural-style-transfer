# backend/app/__init__.py
from app.video_utils import get_webcam_frame, release_webcam, process_video_file, get_video_info
from app.style_transfer import load_style_model, apply_style
from app.temporal_filter import TemporalFilter, AdaptiveTemporalFilter
from app.config import (
    AVAILABLE_STYLES,
    DEFAULT_STYLE,
    get_available_styles,
    get_current_style,
    get_current_model_path,
    set_current_style,
    get_style_recommended_size
)


__all__ = [
    'get_webcam_frame',
    'release_webcam', 
    'process_video_file',
    'get_video_info',
    'load_style_model',
    'apply_style',
    'TemporalFilter',
    'AdaptiveTemporalFilter',
    'OpticalFlowFilter',
    'AVAILABLE_STYLES',
    'DEFAULT_STYLE',
    'get_available_styles',
    'get_current_style',
    'get_current_model_path',
    'set_current_style',
    'get_style_recommended_size'
]