"""
Neural Style Transfer - Model Diagnostic & Test Script
-------------------------------------------------------
backend dizininde çalıştır:
    python app/test_models.py
"""

import re
import os
import sys
import json

import torch
import torch.nn as nn
import numpy as np
from torchvision import transforms
from PIL import Image

# app modülü için path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.style_transfer import (
    StarryNightNet,
    FastStyleNet,
    _clean_starry_state_dict,
    _clean_fast_style_state_dict,
    _build_input_transform,
    _tensor_to_bgr,
)
from app.config import STYLE_PROCESSING


def detect_architecture(state_dict):
    keys = list(state_dict.keys())
    first = keys[0]
    if "ConvBlock" in first:
        return "StarryNightNet"
    if "conv1.conv2d" in first:
        return "FastStyleNet"
    return "Unknown"


def make_test_image(size=256):
    np.random.seed(42)
    img = np.zeros((size, size, 3), dtype=np.uint8)
    for i in range(size):
        img[i, :, 0] = int(50 + (i / size) * 100)
        img[i, :, 1] = int(100 + (i / size) * 80)
        img[i, :, 2] = int(200 - (i / size) * 100)
    noise = np.random.randint(0, 30, (size, size, 3), dtype=np.uint8)
    return np.clip(img.astype(int) + noise, 0, 255).astype(np.uint8)


def score_output(arr):
    mean_val = float(arr.mean())
    std_val = float(arr.std())
    is_white = mean_val > 250
    is_black = mean_val < 5
    is_clipped = (arr.max() - arr.min()) < 10
    if is_black or is_white or is_clipped:
        return 0, mean_val, std_val
    return min(100, int(std_val * 2)) + (50 if 30 < mean_val < 220 else 0), mean_val, std_val


def load_model_for_style(style_id, model_path, device):
    sd = torch.load(model_path, map_location=device, weights_only=True)
    if "state_dict" in sd:
        sd = sd["state_dict"]

    cfg = STYLE_PROCESSING[style_id]
    if cfg["architecture"] == "starry_night":
        model = StarryNightNet()
        cleaned = _clean_starry_state_dict(sd)
    else:
        model = FastStyleNet()
        cleaned = _clean_fast_style_state_dict(sd)

    missing, unexpected = model.load_state_dict(cleaned, strict=False)
    model = model.to(device)
    model.eval()
    return model, missing, unexpected


def test_with_config(model, style_id, size, device):
    cfg = STYLE_PROCESSING[style_id]
    pil_img = Image.fromarray(make_test_image(size))
    transform = _build_input_transform(size, cfg["norm_mode"])
    inp = transform(pil_img).unsqueeze(0).to(device)

    with torch.no_grad():
        out = model(inp)

    arr = _tensor_to_bgr(out, cfg["output_mode"], size, size)
    arr_rgb = arr[:, :, ::-1]
    return score_output(arr_rgb)


MODELS_TO_TEST = {
    "candy": "models/candy.pth",
    "mosaic": "models/mosaic.pth",
    "rain_princess": "models/rain_princess.pth",
    "udnie": "models/udnie.pth",
    "starry_night": "models/Starry_Night_512.pth",
}


def run_diagnostics():
    os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    device = torch.device("cpu")
    results = {}

    print("\n" + "=" * 70)
    print("  NEURAL STYLE TRANSFER — MODEL DIAGNOSTIC REPORT")
    print("=" * 70)

    for model_name, model_path in MODELS_TO_TEST.items():
        print(f"\n{'-' * 60}")
        print(f"  MODEL: {model_name.upper()}")
        print(f"  PATH:  {model_path}")
        print(f"{'-' * 60}")

        if not os.path.exists(model_path):
            print("  [!] Dosya bulunamadi, atlaniyor.")
            results[model_name] = {"error": "file_not_found"}
            continue

        try:
            model, missing, unexpected = load_model_for_style(model_name, model_path, device)
        except Exception as e:
            print(f"  [X] Model yukleme hatasi: {e}")
            results[model_name] = {"error": str(e)}
            continue

        cfg = STYLE_PROCESSING[model_name]
        print(f"  Mimari       : {cfg['architecture']}")
        print(f"  Norm/Output  : {cfg['norm_mode']} / {cfg['output_mode']}")
        if missing:
            print(f"  [!] Eksik keyler ({len(missing)}): {missing[:3]}")
        elif unexpected:
            print(f"  [!] Beklenmeyen ({len(unexpected)}): {unexpected[:3]}")
        else:
            print("  [OK] Tum keyler eslesti.")

        print(f"\n  Process Size Testi:")
        size_scores = {}
        for sz in [256, 384, 512]:
            sc, mn, st = test_with_config(model, model_name, sz, device)
            size_scores[sz] = sc
            flag = "*" if sc >= 80 else "  "
            verdict = "GOOD" if sc >= 80 else ("OK" if sc >= 40 else "BAD")
            print(f"  {flag} {sz}x{sz}: score={sc:3d}  mean={mn:.1f}  std={st:.1f}  {verdict}")

        best_size = max(size_scores, key=size_scores.get)
        best_score = size_scores[best_size]

        results[model_name] = {
            "architecture": cfg["architecture"],
            "norm_mode": cfg["norm_mode"],
            "output_mode": cfg["output_mode"],
            "recommended_size": cfg["recommended_size"],
            "best_size": best_size,
            "best_score": best_score,
            "size_scores": size_scores,
        }

    print("\n\n" + "=" * 70)
    print("  ÖZET")
    print("=" * 70)
    print(f"\n  {'Model':<16} {'Arch':<14} {'Norm':<8} {'Output':<8} {'Size':<6} {'Score'}")
    print(f"  {'-' * 16} {'-' * 14} {'-' * 8} {'-' * 8} {'-' * 6} {'-' * 6}")

    for mn, r in results.items():
        if "error" in r:
            print(f"  {mn:<16} HATA: {r['error']}")
            continue
        print(
            f"  {mn:<16} {r['architecture']:<14} {r['norm_mode']:<8} "
            f"{r['output_mode']:<8} {r['recommended_size']:<6} {r['best_score']}"
        )

    out_path = "model_diagnostic_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n  Sonuclar kaydedildi: {out_path}\n")
    return results


if __name__ == "__main__":
    run_diagnostics()
