"""
Unit tests for visual review metrics (Phase A2).
Tests objective vision criteria using controlled synthetic images.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from synfig_mcp.review.metrics import (
    check_empty_or_uniform,
    check_safe_areas,
    compute_frame_motion,
    compute_ssim,
    detect_flash_strobe,
    detect_luminance_clipping,
    extract_dominant_palette,
    generate_diff_heatmap,
)
from synfig_mcp.review.rubrics import get_rubric, list_available_rubrics


def test_ssim_identical_and_differing() -> None:
    # Identical images must have SSIM = 1.0
    img1 = np.full((120, 160, 3), 128, dtype=np.uint8)
    img2 = np.full((120, 160, 3), 128, dtype=np.uint8)
    assert compute_ssim(img1, img2) == 1.0

    # Distinct images must have lower SSIM
    img_black = np.zeros((120, 160, 3), dtype=np.uint8)
    img_white = np.full((120, 160, 3), 255, dtype=np.uint8)
    assert compute_ssim(img_black, img_white) < 0.1


def test_luminance_clipping() -> None:
    # Pure black image
    img_black = np.zeros((100, 100, 3), dtype=np.uint8)
    res_b = detect_luminance_clipping(img_black)
    assert res_b["crushed_black"] is True
    assert res_b["blown_highlight"] is False
    assert len(res_b["warnings"]) > 0

    # Pure white image
    img_white = np.full((100, 100, 3), 255, dtype=np.uint8)
    res_w = detect_luminance_clipping(img_white)
    assert res_w["blown_highlight"] is True
    assert res_w["crushed_black"] is False
    assert len(res_w["warnings"]) > 0

    # Balanced midtone image
    img_gray = np.full((100, 100, 3), 128, dtype=np.uint8)
    res_g = detect_luminance_clipping(img_gray)
    assert res_g["crushed_black"] is False
    assert res_g["blown_highlight"] is False
    assert len(res_g["warnings"]) == 0


def test_empty_or_uniform_detection() -> None:
    # Fully transparent canvas
    trans = np.zeros((100, 100, 4), dtype=np.uint8)
    res_t = check_empty_or_uniform(trans)
    assert res_t["is_empty"] is True
    assert res_t["is_uniform"] is True

    # Uniform solid color
    solid = np.full((100, 100, 3), 100, dtype=np.uint8)
    res_s = check_empty_or_uniform(solid)
    assert res_s["is_empty"] is False
    assert res_s["is_uniform"] is True

    # High-variance pattern
    np.random.seed(42)
    noise = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    res_n = check_empty_or_uniform(noise)
    assert res_n["is_empty"] is False
    assert res_n["is_uniform"] is False


def test_safe_areas_and_boundary_clipping() -> None:
    img = np.zeros((240, 320, 3), dtype=np.uint8)
    res = check_safe_areas(img)
    assert res["title_safe_box"]["width"] == int(320 * 0.80)
    assert res["action_safe_box"]["width"] == int(320 * 0.90)
    assert res["boundary_clipping_detected"] is False

    # Image with severe edge boundary contrast
    edge_clipped = np.zeros((240, 320, 3), dtype=np.uint8)
    edge_clipped[0:2, 10:100] = 255  # bright stripe cutting off top boundary
    res_clipped = check_safe_areas(edge_clipped)
    assert res_clipped["boundary_clipping_detected"] is True
    assert len(res_clipped["warnings"]) > 0


def test_dominant_palette_extraction() -> None:
    # Image with red, green, blue vertical bands
    img = np.zeros((60, 60, 3), dtype=np.uint8)
    img[:, :20, 0] = 255  # Red
    img[:, 20:40, 1] = 255  # Green
    img[:, 40:, 2] = 255  # Blue

    palette = extract_dominant_palette(img, k=3)
    assert len(palette) == 3
    # Check valid hex formatting
    for color in palette:
        assert color.startswith("#")
        assert len(color) == 7


def test_strobe_photosensitivity_detection() -> None:
    # 6 alternating black and white frames (rapid flash)
    strobe_frames = [
        np.zeros((64, 64, 3), dtype=np.uint8),
        np.full((64, 64, 3), 255, dtype=np.uint8),
        np.zeros((64, 64, 3), dtype=np.uint8),
        np.full((64, 64, 3), 255, dtype=np.uint8),
        np.zeros((64, 64, 3), dtype=np.uint8),
        np.full((64, 64, 3), 255, dtype=np.uint8),
    ]
    res_strobe = detect_flash_strobe(strobe_frames, fps=24.0)
    assert res_strobe["flash_warning"] is True
    assert res_strobe["flashes_per_sec"] >= 3.0
    assert len(res_strobe["warnings"]) > 0

    # Smooth subtle gradual change
    gradual_frames = [np.full((64, 64, 3), 100 + i * 2, dtype=np.uint8) for i in range(6)]
    res_gradual = detect_flash_strobe(gradual_frames, fps=24.0)
    assert res_gradual["flash_warning"] is False
    assert len(res_gradual["warnings"]) == 0


def test_diff_heatmap_generation() -> None:
    img1 = np.zeros((80, 80, 3), dtype=np.uint8)
    img2 = np.zeros((80, 80, 3), dtype=np.uint8)
    img2[20:60, 20:60] = 255  # change center block

    heatmap = generate_diff_heatmap(img1, img2)
    assert isinstance(heatmap, Image.Image)
    assert heatmap.size == (80, 80)
    arr_h = np.array(heatmap)
    # Center block where change occurred should have high red/yellow signal
    center_val = arr_h[40, 40]
    assert center_val[0] > 100  # red channel active for significant delta


def test_motion_delta_computation() -> None:
    img1 = np.full((50, 50, 3), 100, dtype=np.uint8)
    img2 = np.full((50, 50, 3), 100, dtype=np.uint8)
    motion_static = compute_frame_motion(img1, img2)
    assert motion_static["is_static"] is True
    assert motion_static["ssim"] == 1.0

    img3 = np.full((50, 50, 3), 200, dtype=np.uint8)
    motion_active = compute_frame_motion(img1, img3)
    assert motion_active["is_static"] is False
    assert motion_active["mean_pixel_delta"] == 100.0


def test_rubric_resources() -> None:
    assert "Shonen Action" in get_rubric("shonen_action")
    assert "Dark Fantasy" in get_rubric("dark_fantasy")
    assert "Supernatural Noir" in get_rubric("supernatural_noir")
    assert "General" in get_rubric("unknown_style")  # fallback
    assert len(list_available_rubrics()) >= 5
