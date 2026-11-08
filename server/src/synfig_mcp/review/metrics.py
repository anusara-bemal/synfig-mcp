"""
Objective vision metrics for Synfig MCP Visual Review Loop (Phase A2).
Pure PIL + NumPy implementations with zero external network or vision API calls.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from PIL import Image


def compute_ssim(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Compute Structural Similarity Index (SSIM) between two RGB/RGBA images (Wang et al. 2004).
    Expects uint8 numpy arrays [H, W, C] of equal shapes.
    """
    if img1.shape != img2.shape:
        # Resize img2 to match img1
        im2_pil = Image.fromarray(img2).resize((img1.shape[1], img1.shape[0]))
        img2 = np.array(im2_pil)

    # Convert to grayscale float [0, 1]
    def to_gray(arr: np.ndarray) -> np.ndarray:
        if arr.ndim == 3 and arr.shape[2] >= 3:
            # Luminance weights: 0.2989 R + 0.5870 G + 0.1140 B
            gray = 0.2989 * arr[:, :, 0] + 0.5870 * arr[:, :, 1] + 0.1140 * arr[:, :, 2]
        else:
            gray = arr.squeeze().astype(float)
        return gray.astype(float) / 255.0

    y1 = to_gray(img1)
    y2 = to_gray(img2)

    c1 = (0.01 * 1.0) ** 2
    c2 = (0.03 * 1.0) ** 2

    mu1 = float(np.mean(y1))
    mu2 = float(np.mean(y2))

    sigma1_sq = float(np.var(y1))
    sigma2_sq = float(np.var(y2))
    sigma12 = float(np.mean((y1 - mu1) * (y2 - mu2)))

    numerator = (2 * mu1 * mu2 + c1) * (2 * sigma12 + c2)
    denominator = (mu1**2 + mu2**2 + c1) * (sigma1_sq + sigma2_sq + c2)

    if denominator == 0:
        return 1.0

    return max(0.0, min(1.0, float(numerator / denominator)))


def detect_luminance_clipping(
    img: np.ndarray,
    black_thresh: float = 0.02,
    white_thresh: float = 0.98,
    max_percent: float = 0.25,
) -> dict[str, Any]:
    """
    Analyze luminance distribution to detect crushed blacks or blown highlights.
    """
    if img.ndim == 3 and img.shape[2] >= 3:
        lum = (0.2989 * img[:, :, 0] + 0.5870 * img[:, :, 1] + 0.1140 * img[:, :, 2]) / 255.0
    else:
        lum = img.astype(float) / 255.0

    total_pixels = lum.size
    if total_pixels == 0:
        return {
            "crushed_black": False,
            "blown_highlight": False,
            "black_ratio": 0.0,
            "white_ratio": 0.0,
        }

    black_count = int(np.sum(lum <= black_thresh))
    white_count = int(np.sum(lum >= white_thresh))

    black_ratio = black_count / total_pixels
    white_ratio = white_count / total_pixels

    warnings: list[str] = []
    if black_ratio > max_percent:
        warnings.append(
            f"Crushed blacks: {black_ratio * 100:.1f}% of pixels below {black_thresh * 100:.0f}% luminance."
        )
    if white_ratio > max_percent:
        warnings.append(
            f"Blown highlights: {white_ratio * 100:.1f}% of pixels above {white_thresh * 100:.0f}% luminance."
        )

    return {
        "crushed_black": black_ratio > max_percent,
        "blown_highlight": white_ratio > max_percent,
        "black_ratio": round(black_ratio, 4),
        "white_ratio": round(white_ratio, 4),
        "warnings": warnings,
    }


def check_empty_or_uniform(img: np.ndarray, std_thresh: float = 2.0) -> dict[str, Any]:
    """Detect if an image canvas is completely empty (transparent) or solid uniform color."""
    is_empty = False
    is_uniform = False
    warnings: list[str] = []

    if img.ndim == 3 and img.shape[2] == 4:
        # Check alpha channel
        alpha = img[:, :, 3]
        if np.all(alpha == 0):
            is_empty = True
            warnings.append("Canvas is completely transparent (no visible elements).")

    std_val = float(np.std(img[:, :, :3] if img.ndim == 3 else img))
    if std_val < std_thresh:
        is_uniform = True
        warnings.append(
            f"Canvas has uniform solid color (standard deviation {std_val:.2f} < {std_thresh})."
        )

    return {
        "is_empty": is_empty,
        "is_uniform": is_uniform,
        "std_dev": round(std_val, 2),
        "warnings": warnings,
    }


def check_safe_areas(img: np.ndarray) -> dict[str, Any]:
    """
    Check standard SMPTE/EBU Action Safe (90%) and Title Safe (80%) margins.
    Detects if high-contrast edges or significant non-background drawing cuts off at canvas boundaries.
    """
    h, w = img.shape[:2]
    title_margin_x = int(w * 0.10)
    title_margin_y = int(h * 0.10)
    action_margin_x = int(w * 0.05)
    action_margin_y = int(h * 0.05)

    warnings: list[str] = []

    # Check pixel gradients along the canvas outermost 2 pixels (edge bleed / boundary clipping)
    top_edge = img[0:2, :, :3]
    bottom_edge = img[h - 2 : h, :, :3]
    left_edge = img[:, 0:2, :3]
    right_edge = img[:, w - 2 : w, :3]

    edge_std = float(
        np.mean([np.std(top_edge), np.std(bottom_edge), np.std(left_edge), np.std(right_edge)])
    )
    has_boundary_clipping = edge_std > 20.0
    if has_boundary_clipping:
        warnings.append("Drawing elements appear abruptly clipped at outer canvas boundaries.")

    return {
        "title_safe_box": {
            "x": title_margin_x,
            "y": title_margin_y,
            "width": w - (2 * title_margin_x),
            "height": h - (2 * title_margin_y),
        },
        "action_safe_box": {
            "x": action_margin_x,
            "y": action_margin_y,
            "width": w - (2 * action_margin_x),
            "height": h - (2 * action_margin_y),
        },
        "boundary_clipping_detected": has_boundary_clipping,
        "warnings": warnings,
    }


def extract_dominant_palette(img: np.ndarray, k: int = 5) -> list[str]:
    """Extract dominant color palette in hex codes (#RRGGBB)."""
    # Sample down for fast extraction
    pil_img = Image.fromarray(img).convert("RGB").resize((64, 64), Image.Resampling.NEAREST)
    quantized = pil_img.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
    palette_data = quantized.getpalette() or []

    hex_colors: list[str] = []
    num_available = len(palette_data) // 3
    for i in range(min(k, num_available)):
        r = palette_data[i * 3]
        g = palette_data[i * 3 + 1]
        b = palette_data[i * 3 + 2]
        hex_colors.append(f"#{r:02x}{g:02x}{b:02x}")

    if not hex_colors:
        hex_colors.append("#000000")

    return hex_colors


def detect_flash_strobe(frames: list[np.ndarray], fps: float = 24.0) -> dict[str, Any]:
    """
    WCAG 2.3.1 Photosensitivity Strobe Check:
    Warns if luminance shifts > 20% occur more than 3 times within 1 second.
    """
    if len(frames) < 2:
        return {"flash_warning": False, "max_delta": 0.0, "flashes_per_sec": 0.0, "warnings": []}

    avg_lums: list[float] = []
    for f in frames:
        if f.ndim == 3 and f.shape[2] >= 3:
            lum = (0.2989 * f[:, :, 0] + 0.5870 * f[:, :, 1] + 0.1140 * f[:, :, 2]) / 255.0
        else:
            lum = f.astype(float) / 255.0
        avg_lums.append(float(np.mean(lum)))

    deltas = [abs(avg_lums[i] - avg_lums[i - 1]) for i in range(1, len(avg_lums))]
    large_flashes = [d for d in deltas if d >= 0.20]
    max_delta = max(deltas) if deltas else 0.0

    duration = max(1.0, len(frames) / fps)
    flashes_per_sec = len(large_flashes) / duration
    strobe_detected = flashes_per_sec >= 3.0

    warnings: list[str] = []
    if strobe_detected:
        warnings.append(
            f"Photosensitivity Strobe Warning: {len(large_flashes)} rapid flashes detected "
            f"({flashes_per_sec:.1f} Hz, exceeding WCAG 2.3.1 safe threshold of 3 Hz)."
        )

    return {
        "flash_warning": strobe_detected,
        "max_delta": round(max_delta, 3),
        "flashes_per_sec": round(flashes_per_sec, 2),
        "warnings": warnings,
    }


def compute_frame_motion(img1: np.ndarray, img2: np.ndarray) -> dict[str, Any]:
    """Compute per-frame motion metrics (SSIM, pixel delta percentage, mean absolute difference)."""
    ssim = compute_ssim(img1, img2)
    diff = np.abs(img1.astype(float) - img2.astype(float))
    mean_abs_diff = float(np.mean(diff))

    # A pixel is considered 'changed' if any RGB channel changed by > 5
    changed_mask = np.any(diff[:, :, :3] > 5, axis=2) if diff.ndim == 3 else diff > 5
    changed_ratio = float(np.sum(changed_mask) / changed_mask.size)

    return {
        "ssim": round(ssim, 4),
        "mean_pixel_delta": round(mean_abs_diff, 2),
        "pixel_change_ratio": round(changed_ratio, 4),
        "is_static": changed_ratio < 0.001,
    }


def generate_diff_heatmap(img1: np.ndarray, img2: np.ndarray) -> Image.Image:
    """
    Generate an intuitive diff heatmap image between two animation iterations.
    - Black/Dark Navy: unchanged (difference ~ 0)
    - Cyan/Green: minor adjustments
    - Yellow/Orange: moderate positional changes
    - Red/Magenta: major changes / deletions / additions
    """
    if img1.shape != img2.shape:
        im2_pil = Image.fromarray(img2).resize((img1.shape[1], img1.shape[0]))
        img2 = np.array(im2_pil)

    diff = np.abs(img1[:, :, :3].astype(float) - img2[:, :, :3].astype(float))
    # Euclidean distance normalized [0, 1]
    magnitude = np.sqrt(np.sum(diff**2, axis=2)) / (math.sqrt(3 * (255**2)))

    h, w = magnitude.shape
    heatmap = np.zeros((h, w, 3), dtype=np.uint8)

    # Simple colormap interpolation:
    # 0.0: [10, 15, 30] (dark navy)
    # 0.2: [20, 100, 200] (cyan)
    # 0.5: [50, 220, 50] (green)
    # 0.8: [240, 180, 20] (yellow)
    # 1.0: [255, 30, 30] (red)
    r = np.clip(magnitude * 2.5 * 255, 0, 255).astype(np.uint8)
    g = np.clip((1.0 - np.abs(magnitude - 0.4) * 2.0) * 255, 0, 255).astype(np.uint8)
    b = np.clip((0.3 - magnitude) * 3.0 * 255, 0, 255).astype(np.uint8)

    heatmap[:, :, 0] = r
    heatmap[:, :, 1] = g
    heatmap[:, :, 2] = b

    return Image.fromarray(heatmap, mode="RGB")
