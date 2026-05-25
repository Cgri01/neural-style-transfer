import re
import torch
import torch.nn as nn
import numpy as np
import cv2
import logging
import time
import concurrent.futures
from torchvision import transforms
from PIL import Image
from app.config import get_current_style, get_style_processing_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_model_cache = {}
_global_processor = None


#Starry NİghM Mimarisi
class ConvLayer(nn.Module):
    def __init__(self, in_c, out_c, kernel_size, stride):
        super().__init__()
        pad = kernel_size // 2
        self.conv = nn.Conv2d(in_c, out_c, kernel_size, stride, pad)
        self.norm = nn.InstanceNorm2d(out_c, affine=True)

    def forward(self, x):
        return torch.relu(self.norm(self.conv(x)))


class ResBlock_SN(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = ConvLayer(channels, channels, 3, 1)
        self.conv2 = ConvLayer(channels, channels, 3, 1)

    def forward(self, x):
        return x + self.conv2.norm(self.conv2.conv(
            torch.relu(self.conv1.norm(self.conv1.conv(x)))))


class DeconvLayer(nn.Module):
    def __init__(self, in_c, out_c, kernel_size, stride, last=False):
        super().__init__()
        if last:
            self.conv = nn.Conv2d(in_c, out_c, kernel_size, stride, kernel_size // 2)
            self.norm = None
        else:
            self.conv_transpose = nn.ConvTranspose2d(
                in_c, out_c, kernel_size, stride, padding=1, output_padding=1)
            self.norm = nn.InstanceNorm2d(out_c, affine=True)
        self.last = last

    def forward(self, x):
        if self.last:
            return self.conv(x)
        return torch.relu(self.norm(self.conv_transpose(x)))


class StarryNightNet(nn.Module):
    def __init__(self):
        super().__init__()
        self.ConvBlock = nn.ModuleList([
            ConvLayer(3, 32, 9, 1),
            nn.Identity(),
            ConvLayer(32, 64, 3, 2),
            nn.Identity(),
            ConvLayer(64, 128, 3, 2),
        ])
        self.ResidualBlock = nn.ModuleList([ResBlock_SN(128) for _ in range(5)])
        self.DeconvBlock = nn.ModuleList([
            DeconvLayer(128, 64, 3, 2),
            nn.Identity(),
            DeconvLayer(64, 32, 3, 2),
            nn.Identity(),
            DeconvLayer(32, 3, 9, 1, last=True),
        ])

    def forward(self, x):
        x = self.ConvBlock[0](x)
        x = self.ConvBlock[2](x)
        x = self.ConvBlock[4](x)
        for res in self.ResidualBlock:
            x = res(x)
        x = self.DeconvBlock[0](x)
        x = self.DeconvBlock[2](x)
        x = self.DeconvBlock[4](x)
        return torch.tanh(x)



class FastConvLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride):
        super().__init__()
        reflection_padding = kernel_size // 2
        self.reflection_pad = nn.ReflectionPad2d(reflection_padding)
        self.conv2d = nn.Conv2d(in_channels, out_channels, kernel_size, stride)

    def forward(self, x):
        return self.conv2d(self.reflection_pad(x))


class FastResidualBlock(nn.Module):
    def __init__(self, channels):
        super().__init__()
        self.conv1 = FastConvLayer(channels, channels, 3, 1)
        self.in1 = nn.InstanceNorm2d(channels, affine=True)
        self.conv2 = FastConvLayer(channels, channels, 3, 1)
        self.in2 = nn.InstanceNorm2d(channels, affine=True)
        self.relu = nn.ReLU()

    def forward(self, x):
        residual = x
        out = self.relu(self.in1(self.conv1(x)))
        out = self.in2(self.conv2(out))
        return out + residual


class FastUpsampleConvLayer(nn.Module):
    def __init__(self, in_channels, out_channels, kernel_size, stride, upsample=None):
        super().__init__()
        self.upsample = upsample
        reflection_padding = kernel_size // 2
        self.reflection_pad = nn.ReflectionPad2d(reflection_padding)
        self.conv2d = nn.Conv2d(in_channels, out_channels, kernel_size, stride)

    def forward(self, x):
        if self.upsample:
            x = nn.functional.interpolate(
                x, mode="nearest", scale_factor=self.upsample
            )
        return self.conv2d(self.reflection_pad(x))


class FastStyleNet(nn.Module):
    """candy, mosaic, rain_princess, udnie"""

    def __init__(self):
        super().__init__()
        self.conv1 = FastConvLayer(3, 32, 9, 1)
        self.in1 = nn.InstanceNorm2d(32, affine=True)
        self.conv2 = FastConvLayer(32, 64, 3, 2)
        self.in2 = nn.InstanceNorm2d(64, affine=True)
        self.conv3 = FastConvLayer(64, 128, 3, 2)
        self.in3 = nn.InstanceNorm2d(128, affine=True)
        self.res1 = FastResidualBlock(128)
        self.res2 = FastResidualBlock(128)
        self.res3 = FastResidualBlock(128)
        self.res4 = FastResidualBlock(128)
        self.res5 = FastResidualBlock(128)
        self.deconv1 = FastUpsampleConvLayer(128, 64, 3, 1, upsample=2)
        self.in4 = nn.InstanceNorm2d(64, affine=True)
        self.deconv2 = FastUpsampleConvLayer(64, 32, 3, 1, upsample=2)
        self.in5 = nn.InstanceNorm2d(32, affine=True)
        self.deconv3 = FastConvLayer(32, 3, 9, 1)
        self.relu = nn.ReLU()

    def forward(self, x):
        y = self.relu(self.in1(self.conv1(x)))
        y = self.relu(self.in2(self.conv2(y)))
        y = self.relu(self.in3(self.conv3(y)))
        y = self.res1(y)
        y = self.res2(y)
        y = self.res3(y)
        y = self.res4(y)
        y = self.res5(y)
        y = self.relu(self.in4(self.deconv1(y)))
        y = self.relu(self.in5(self.deconv2(y)))
        return self.deconv3(y)


# Geriye dönük uyumluluk
CandyNet = FastStyleNet


def _clean_starry_state_dict(state_dict):
    return {
        k: v for k, v in state_dict.items()
        if "running_mean" not in k
        and "running_var" not in k
        and "num_batches_tracked" not in k
    }


def _clean_fast_style_state_dict(state_dict):
    
    cleaned = {}
    for k, v in state_dict.items():
        if re.search(r"in\d+\.running_(mean|var)$", k):
            continue
        if "num_batches_tracked" in k:
            continue
        cleaned[k] = v
    return cleaned


def detect_and_load_model(model_path, device):
    state_dict = torch.load(model_path, map_location=device)
    if "state_dict" in state_dict:
        state_dict = state_dict["state_dict"]

    keys = list(state_dict.keys())
    first_key = keys[0]

    if "ConvBlock" in first_key:
        logger.info("Architecture: StarryNightNet")
        model = StarryNightNet()
        cleaned = _clean_starry_state_dict(state_dict)
    elif "conv1.conv2d" in first_key:
        logger.info("Architecture: FastStyleNet")
        model = FastStyleNet()
        cleaned = _clean_fast_style_state_dict(state_dict)
    else:
        logger.warning("Unknown architecture, FastStyleNet trying")
        model = FastStyleNet()
        cleaned = _clean_fast_style_state_dict(state_dict)

    missing, unexpected = model.load_state_dict(cleaned, strict=False)
    if missing:
        logger.warning(f"Missing keys ({len(missing)}): {missing[:3]}")
    if unexpected:
        logger.warning(f"Unexpected keys ({len(unexpected)}): {unexpected[:3]}")

    model = model.to(device)
    model.eval()
    return model


def load_style_model(model_path, device=None, use_gpu_if_available=True):
    if device is None:
        if use_gpu_if_available and torch.cuda.is_available():
            device = torch.device("cuda")
            logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        else:
            device = torch.device("cpu")
            logger.info("CPU using")

    logger.info(f"Model loading: {model_path}")
    model = detect_and_load_model(model_path, device)

    if device.type == "cuda":
        torch.backends.cudnn.benchmark = True

    logger.info("Model uploaded successfully")
    return model, device


def _resolve_process_size(frame, device, target_size, use_adaptive_size, style_config):
    if not use_adaptive_size:
        return target_size

    recommended = style_config.get("recommended_size", target_size)
    original_h, original_w = frame.shape[:2]
    min_dim = min(original_h, original_w)

    if min_dim < 300:
        adaptive = 256
    elif min_dim < 600:
        adaptive = 384
    elif min_dim < 1000:
        adaptive = 512
    else:
        adaptive = 640

    process_size = min(adaptive, recommended) if recommended else adaptive

    if device.type == "cuda":
        gpu_mem = torch.cuda.get_device_properties(device).total_memory / 1e9
        if gpu_mem < 4:
            process_size = min(process_size, 384)

    return process_size


def _build_input_transform(process_size, norm_mode):
    
    base = [
        transforms.Resize(process_size),
        transforms.CenterCrop(process_size),
        transforms.ToTensor(),
    ]
    if norm_mode == "raw255":
        base.append(transforms.Lambda(lambda x: x * 255.0))
    elif norm_mode == "half":
        base.append(transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5]))
    elif norm_mode == "raw1":
        pass
    elif norm_mode == "imagenet":
        base.append(transforms.Normalize(
            mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
        ))
    else:
        raise ValueError(f"Unknown norm_mode: {norm_mode}")
    return transforms.Compose(base)


def _tensor_to_bgr(output_tensor, output_mode, original_h, original_w):
    output_tensor = output_tensor.squeeze(0).cpu()

   
    if output_mode == "tanh":
        output_tensor = (output_tensor * 0.5 + 0.5).clamp(0, 1)
        output_array = (output_tensor * 255).byte().numpy().transpose(1, 2, 0)
    elif output_mode == "clamp":
        output_array = output_tensor.clamp(0, 255).numpy().transpose(1, 2, 0).astype(np.uint8)
    else:
        raise ValueError(f"Unknown output_mode: {output_mode}")

    output_bgr = cv2.cvtColor(output_array, cv2.COLOR_RGB2BGR)
    if (output_bgr.shape[0], output_bgr.shape[1]) != (original_h, original_w):
        output_bgr = cv2.resize(
            output_bgr, (original_w, original_h), interpolation=cv2.INTER_LANCZOS4
        )
    return output_bgr


def apply_starry_night_style(frame, model, device, target_size=512, use_adaptive_size=True):
    style_config = get_style_processing_config("starry_night")
    return _apply_style_with_config(frame, model, device, style_config, target_size, use_adaptive_size)


def apply_fast_style(frame, model, device, style_id, target_size=384, use_adaptive_size=True):
    style_config = get_style_processing_config(style_id)
    return _apply_style_with_config(frame, model, device, style_config, target_size, use_adaptive_size)


def _apply_style_with_config(frame, model, device, style_config, target_size, use_adaptive_size):
    if frame is None:
        return None

    original_h, original_w = frame.shape[:2]
    process_size = _resolve_process_size(
        frame, device, target_size, use_adaptive_size, style_config
    )

    pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    transform = _build_input_transform(process_size, style_config["norm_mode"])
    input_batch = transform(pil_image).unsqueeze(0).to(device)

    with torch.no_grad():
        output_tensor = model(input_batch)

    return _tensor_to_bgr(output_tensor, style_config["output_mode"], original_h, original_w)


def apply_style(frame, model, device, target_size=512, use_adaptive_size=True, style_id=None):
    """Model tipine göre doğru işlem pipeline'ını seçer."""
    if frame is None:
        return None

    if style_id is None:
        style_id = get_current_style()

    if isinstance(model, StarryNightNet):
        return apply_starry_night_style(frame, model, device, target_size, use_adaptive_size)

    if isinstance(model, FastStyleNet):
        return apply_fast_style(frame, model, device, style_id, target_size, use_adaptive_size)

    logger.warning(f"Unknown model type: {type(model)}, fast style trying")
    return apply_fast_style(frame, model, device, style_id, target_size, use_adaptive_size)


class StyleTransferProcessor:
    def __init__(self, model, device, style_id=None, timeout_seconds=5.0, enable_fallback=True):
        self.model = model
        self.device = device
        self.style_id = style_id or get_current_style()
        self.timeout_seconds = timeout_seconds
        self.enable_fallback = enable_fallback
        self.last_successful_frame = None
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5

    def apply_style_safe(self, frame, target_size=512):
        if frame is None:
            return self._get_fallback_frame()
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    apply_style, frame, self.model, self.device,
                    target_size, False, self.style_id
                )
                result = future.result(timeout=self.timeout_seconds)
                self.consecutive_errors = 0
                self.last_successful_frame = result
                return result
        except Exception as e:
            logger.error(f"Style transfer error: {e}")
            return self._get_fallback_frame()

    def _get_fallback_frame(self):
        self.consecutive_errors += 1
        if self.enable_fallback and self.last_successful_frame is not None:
            return self.last_successful_frame.copy()
        return np.zeros((480, 640, 3), dtype=np.uint8)

    def reset(self):
        self.last_successful_frame = None
        self.consecutive_errors = 0


def reset_processor():
    global _global_processor
    _global_processor = None


def get_processor(model, device, style_id=None):
    global _global_processor
    style_id = style_id or get_current_style()
    if (
        _global_processor is None
        or _global_processor.model is not model
        or _global_processor.style_id != style_id
    ):
        _global_processor = StyleTransferProcessor(model, device, style_id=style_id)
    return _global_processor


def apply_style_with_fallback(frame, model, device, target_size=512, use_adaptive_size=True, style_id=None):
    style_id = style_id or get_current_style()
    processor = get_processor(model, device, style_id)
    try:
        result = apply_style(
            frame, model, device, target_size, use_adaptive_size, style_id
        )
        if result is not None:
            processor.last_successful_frame = result
            processor.consecutive_errors = 0
            return result
    except Exception as e:
        logger.error(f"apply_style error: {e}")
    return processor._get_fallback_frame()


def get_cached_model(style_id=None, force_reload=False):
    global _model_cache

    if style_id is None:
        style_id = get_current_style()

    if not force_reload and style_id in _model_cache:
        cached = _model_cache[style_id]
        logger.info(f"Loaded from cache: {cached['name']}")
        return cached["model"], cached["device"], cached["style_info"]

    from app.config import AVAILABLE_STYLES
    style_info = AVAILABLE_STYLES.get(style_id)
    if not style_info:
        raise ValueError(f"Style could not find: {style_id}")
    if not style_info.get("is_available", False):
        raise ValueError(f"Style can not use yet: {style_id}")

    model, device = load_style_model(style_info["path"], use_gpu_if_available=True)

    _model_cache[style_id] = {
        "model": model,
        "device": device,
        "style_info": style_info,
        "name": style_info["name"],
    }
    return model, device, style_info


def reload_current_style():
    reset_processor()
    return get_cached_model(get_current_style(), force_reload=True)


def get_available_styles_info():
    from app.config import get_available_styles
    return get_available_styles()
