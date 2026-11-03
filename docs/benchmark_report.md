# Synfig MCP Feature Capability & Benchmark Report

> Evaluated against: **Synfig Studio 1.5.5** on `win32`

## Executive Summary

- **Overall Score**: `100.0 / 100.0`
- **Rank**: **S+ (Production Grade - Full Compatibility)**
- **Features Tested**: `40`
- **Passing Rate**: `40 / 40` (100.0%)

## Capability Score Breakdown by Category

| Category | Passed | Total | Score | Avg Latency |
| :--- | :---: | :---: | :---: | :---: |
| **System** | 4 | 4 | 100.0% | 286.5ms |
| **Project** | 8 | 8 | 100.0% | 3.9ms |
| **Layers** | 6 | 6 | 100.0% | 104.5ms |
| **Shapes** | 4 | 4 | 100.0% | 2.2ms |
| **Filters** | 4 | 4 | 100.0% | 1.4ms |
| **Animation** | 4 | 4 | 100.0% | 3.3ms |
| **Rigging** | 2 | 2 | 100.0% | 6.5ms |
| **Assets** | 1 | 1 | 100.0% | 10.8ms |
| **Rendering** | 4 | 4 | 100.0% | 415.2ms |
| **Batch** | 3 | 3 | 100.0% | 6.1ms |

## Detailed Feature Test Breakdown

| Test Name | Category | Status | Latency | Message |
| :--- | :--- | :---: | :---: | :--- |
| `synfig_doctor` | System | **PASS** | 1143.0ms | OK |
| `synfig_version` | System | **PASS** | 2.8ms | OK |
| `list_render_targets` | System | **PASS** | 0.0ms | OK |
| `list_layer_types` | System | **PASS** | 0.1ms | OK |
| `create_project` | Project | **PASS** | 5.1ms | OK |
| `canvas_properties` | Project | **PASS** | 3.3ms | OK |
| `set_fps_and_time_range` | Project | **PASS** | 0.3ms | OK |
| `save_and_reopen_sif` | Project | **PASS** | 6.4ms | OK |
| `save_and_reopen_sifz` | Project | **PASS** | 6.4ms | OK |
| `save_and_reopen_sfg` | Project | **PASS** | 6.1ms | OK |
| `duplicate_project` | Project | **PASS** | 3.6ms | OK |
| `validate_project` | Project | **PASS** | 0.1ms | OK |
| `add_and_list_layers` | Layers | **PASS** | 305.5ms | OK |
| `layer_parameters` | Layers | **PASS** | 0.1ms | OK |
| `layer_blending_and_opacity` | Layers | **PASS** | 0.2ms | OK |
| `layer_reorder_and_zdepth` | Layers | **PASS** | 320.4ms | OK |
| `layer_enable_disable` | Layers | **PASS** | 0.2ms | OK |
| `layer_group_and_ungroup` | Layers | **PASS** | 0.3ms | OK |
| `shape_circle_rect_polygon` | Shapes | **PASS** | 4.9ms | OK |
| `shape_star_and_text` | Shapes | **PASS** | 0.7ms | OK |
| `shape_bline_and_outlines` | Shapes | **PASS** | 1.3ms | OK |
| `gradients_and_patterns` | Shapes | **PASS** | 1.7ms | OK |
| `filter_blur_motion_radial` | Filters | **PASS** | 1.0ms | OK |
| `filter_color_correct_halftone` | Filters | **PASS** | 1.3ms | OK |
| `filter_transforms_and_twirl` | Filters | **PASS** | 2.1ms | OK |
| `filter_bevel_and_shade` | Filters | **PASS** | 1.2ms | OK |
| `animate_waypoints_and_interpolation` | Animation | **PASS** | 5.4ms | OK |
| `keyframes_management` | Animation | **PASS** | 0.3ms | OK |
| `timeloop_and_timeoffset` | Animation | **PASS** | 0.7ms | OK |
| `bake_animation` | Animation | **PASS** | 6.8ms | OK |
| `create_and_link_bones` | Rigging | **PASS** | 6.4ms | OK |
| `export_value_and_link_params` | Rigging | **PASS** | 6.7ms | OK |
| `import_asset_and_embed_image` | Assets | **PASS** | 10.8ms | OK |
| `render_single_png_frame` | Rendering | **PASS** | 323.9ms | OK |
| `render_preview_and_thumbnail` | Rendering | **PASS** | 628.4ms | OK |
| `render_animated_gif` | Rendering | **PASS** | 708.4ms | OK |
| `get_render_status_and_jobs` | Rendering | **PASS** | 0.2ms | OK |
| `batch_operations_atomic` | Batch | **PASS** | 5.5ms | OK |
| `undo_and_redo_history` | Batch | **PASS** | 5.6ms | OK |
| `project_diffing` | Batch | **PASS** | 7.1ms | OK |

---
*Report generated automatically by `scripts/benchmark.py`.*