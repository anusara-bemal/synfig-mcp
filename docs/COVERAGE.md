# Synfig MCP Feature Coverage Matrix

> **Target: v0.8.0-rc1 Studio-Grade Quality Gate**
> Generated automatically via Synfig binary introspection (`synfig --layers`, `--layer-info`, `--valuenodes`, `--targets`, `--renderers`).
> Never hand-maintained. Enforced by CI test: `tests/unit/test_coverage_matrix.py`.

## 1. Executive Summary

| Category | Total Introspected | Fully Supported | Coverage % | Headless Tested | Live Bridge Tested |
|---|---|---|---|---|---|
| **Layers** | 55 | 50 | **90.9%** | 6 | 5 |
| **Parameters** | 455 | 445 | **97.8%** | - | - |
| **ValueNodes** | 69 | 69 | **100.0%** | - | - |
| **Render Targets** | 13 | 7 | **53.8%** | - | 5 |

---

## 2. Layer Types Coverage

| Layer Type | Localized Name | Version | Read | Write | Headless | Live | Recipe/Sample | Status | Notes / Limitations |
|---|---|---|---|---|---|---|---|---|---|
| `advanced_outline` | Advanced Outline | 0.3 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 22 parameters introspected |
| `bevel` | Bevel | 0.3 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 12 parameters introspected |
| `blur` | Blur | 0.3 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 5 parameters introspected |
| `checker_board` | Checkerboard | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 7 parameters introspected |
| `chromakey` | Chroma Key | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 8 parameters introspected |
| `circle` | Circle | 0.2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Supported | 8 parameters introspected |
| `clamp` | Clamp | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 4 parameters introspected |
| `colorcorrect` | Color Correct | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 6 parameters introspected |
| `conical_gradient` | Conical Gradient | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 7 parameters introspected |
| `curve_gradient` | Curve Gradient | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 11 parameters introspected |
| `curve_warp` | Curve Warp | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 6 parameters introspected |
| `duplicate` | Duplicate | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 4 parameters introspected |
| `filter_group` | Filter Group | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 10 parameters introspected |
| `freetime` | Free Time | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚠️ Advanced | Custom timeloop curve retiming layer |
| `group` | Group | 0.3 | ✅ | ✅ | ✅ | ⚪ | ✅ | ✅ Supported | 14 parameters introspected |
| `halftone2` | Halftone 2 | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 9 parameters introspected |
| `halftone3` | Halftone 3 | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 15 parameters introspected |
| `import` | Import Image | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 9 parameters introspected |
| `inside_out` | Inside Out | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 1 parameters introspected |
| `julia` | Julia Set | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚠️ Experimental | Fractal mathematical generator; non-vector pixel synthesis |
| `linear_gradient` | Linear Gradient | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 8 parameters introspected |
| `lumakey` | Luma Key | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 1 parameters introspected |
| `mandelbrot` | Mandelbrot Set | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚠️ Experimental | Fractal mathematical generator; non-vector pixel synthesis |
| `metaballs` | Metaballs | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 10 parameters introspected |
| `motion_blur` | Motion Blur | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 5 parameters introspected |
| `noise` | Noise Gradient | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 12 parameters introspected |
| `noise_distort` | Noise Distort | 0.0 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 10 parameters introspected |
| `outline` | Outline | 0.3 | ✅ | ✅ | ⚪ | ⚪ | ✅ | ✅ Supported | 17 parameters introspected |
| `plant` | Plant | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 20 parameters introspected |
| `polygon` | Polygon | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 11 parameters introspected |
| `radial_blur` | Radial Blur | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 6 parameters introspected |
| `radial_gradient` | Radial Gradient | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 8 parameters introspected |
| `rectangle` | Rectangle | 0.2 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Supported | 12 parameters introspected |
| `region` | Region | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 11 parameters introspected |
| `rotate` | Rotate | 0.1 | ✅ | ✅ | ⚪ | ✅ | ⚪ | ✅ Supported | 2 parameters introspected |
| `shade` | Shade | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 8 parameters introspected |
| `simple_circle` | Simple Circle | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 6 parameters introspected |
| `skeleton` | Skeleton | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 4 parameters introspected |
| `skeleton_deformation` | [Skeleton Deformation] | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 8 parameters introspected |
| `solid_color` | Solid Color | 0.1 | ✅ | ✅ | ✅ | ⚪ | ✅ | ✅ Supported | 4 parameters introspected |
| `sound` | Sound | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 4 parameters introspected |
| `spherize` | Spherize | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 5 parameters introspected |
| `spiral_gradient` | Spiral Gradient | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 8 parameters introspected |
| `star` | Star | 0.1 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Supported | 15 parameters introspected |
| `stretch` | Stretch | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 2 parameters introspected |
| `stroboscope` | Stroboscope | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 2 parameters introspected |
| `super_sample` | Super Sample | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚠️ Legacy | Software supersampling filter superseded by Cairo/renderer antialiasing |
| `switch` | Switch | 0.0 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 12 parameters introspected |
| `text` | Text | 0.5 | ✅ | ✅ | ✅ | ✅ | ⚪ | ✅ Supported | 18 parameters introspected |
| `timeloop` | Time Loop | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 6 parameters introspected |
| `translate` | Translate | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 1 parameters introspected |
| `twirl` | Twirl | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 5 parameters introspected |
| `warp` | Perspective | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 8 parameters introspected |
| `xor_pattern` | XOR Pattern | 0.2 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ⚠️ Deprecated | Legacy bitwise test pattern layer |
| `zoom` | Scale | 0.1 | ✅ | ✅ | ⚪ | ⚪ | ⚪ | ✅ Supported | 2 parameters introspected |

---

## 3. Render Targets Coverage

| Target Module | Supported | Verified in Tests | Status | Limitations / Purpose |
|---|---|---|---|---|
| `bmp` | ✅ | ⚪ | Supported | Standard video or image raster target |
| `dv` | ❌ | ⚪ | Specialized / Non-Production | Target 'dv' is an uncompressed/specialized output module |
| `ffmpeg` | ✅ | ✅ | Supported | Standard video or image raster target |
| `gif` | ✅ | ✅ | Supported | Standard video or image raster target |
| `jpeg` | ✅ | ⚪ | Supported | Standard video or image raster target |
| `libav` | ✅ | ✅ | Supported | Standard video or image raster target |
| `magick++` | ❌ | ⚪ | Specialized / Non-Production | Target 'magick++' is an uncompressed/specialized output module |
| `null` | ❌ | ⚪ | Specialized / Non-Production | Target 'null' is an uncompressed/specialized output module |
| `null-tile` | ❌ | ⚪ | Specialized / Non-Production | Target 'null-tile' is an uncompressed/specialized output module |
| `png` | ✅ | ✅ | Supported | Standard video or image raster target |
| `png-spritesheet` | ✅ | ✅ | Supported | Standard video or image raster target |
| `ppm` | ❌ | ⚪ | Specialized / Non-Production | Target 'ppm' is an uncompressed/specialized output module |
| `yuv420p` | ❌ | ⚪ | Specialized / Non-Production | Target 'yuv420p' is an uncompressed/specialized output module |

---

## 4. ValueNodes Coverage

Total introspected valuenodes: **69**.
Synfig MCP supports reading and dynamic linking/exporting of all native valuenodes via `valuenode_export`, `valuenode_unexport`, and `param_connect`.

<details>
<summary><strong>Click to expand full valuenodes list (69 types)</strong></summary>

| ValueNode Name | Read | Write / Link | Status |
|---|---|---|---|
| `absolute` | ✅ | ✅ | Supported |
| `add` | ✅ | ✅ | Supported |
| `and` | ✅ | ✅ | Supported |
| `anglestring` | ✅ | ✅ | Supported |
| `animated_file` | ✅ | ✅ | Supported |
| `atan2` | ✅ | ✅ | Supported |
| `average` | ✅ | ✅ | Supported |
| `bline` | ✅ | ✅ | Supported |
| `blinecalctangent` | ✅ | ✅ | Supported |
| `blinecalcvertex` | ✅ | ✅ | Supported |
| `blinecalcwidth` | ✅ | ✅ | Supported |
| `blinerevtangent` | ✅ | ✅ | Supported |
| `bone` | ✅ | ✅ | Supported |
| `bone_link` | ✅ | ✅ | Supported |
| `bone_root` | ✅ | ✅ | Supported |
| `boneinfluence` | ✅ | ✅ | Supported |
| `boneweightpair` | ✅ | ✅ | Supported |
| `compare` | ✅ | ✅ | Supported |
| `composite` | ✅ | ✅ | Supported |
| `cos` | ✅ | ✅ | Supported |
| `derivative` | ✅ | ✅ | Supported |
| `dilist` | ✅ | ✅ | Supported |
| `dotproduct` | ✅ | ✅ | Supported |
| `duplicate` | ✅ | ✅ | Supported |
| `dynamic` | ✅ | ✅ | Supported |
| `dynamic_list` | ✅ | ✅ | Supported |
| `exp` | ✅ | ✅ | Supported |
| `fromangle` | ✅ | ✅ | Supported |
| `fromint` | ✅ | ✅ | Supported |
| `fromreal` | ✅ | ✅ | Supported |
| `gradient_rotate` | ✅ | ✅ | Supported |
| `gradientcolor` | ✅ | ✅ | Supported |
| `greyed` | ✅ | ✅ | Supported |
| `intstring` | ✅ | ✅ | Supported |
| `join` | ✅ | ✅ | Supported |
| `linear` | ✅ | ✅ | Supported |
| `logarithm` | ✅ | ✅ | Supported |
| `map_range` | ✅ | ✅ | Supported |
| `modulo` | ✅ | ✅ | Supported |
| `not` | ✅ | ✅ | Supported |
| `or` | ✅ | ✅ | Supported |
| `power` | ✅ | ✅ | Supported |
| `radial_composite` | ✅ | ✅ | Supported |
| `random` | ✅ | ✅ | Supported |
| `range` | ✅ | ✅ | Supported |
| `realstring` | ✅ | ✅ | Supported |
| `reciprocal` | ✅ | ✅ | Supported |
| `reference` | ✅ | ✅ | Supported |
| `repeat_gradient` | ✅ | ✅ | Supported |
| `reverse` | ✅ | ✅ | Supported |
| `scale` | ✅ | ✅ | Supported |
| `segcalctangent` | ✅ | ✅ | Supported |
| `segcalcvertex` | ✅ | ✅ | Supported |
| `sine` | ✅ | ✅ | Supported |
| `static_list` | ✅ | ✅ | Supported |
| `step` | ✅ | ✅ | Supported |
| `stripes` | ✅ | ✅ | Supported |
| `subtract` | ✅ | ✅ | Supported |
| `switch` | ✅ | ✅ | Supported |
| `timed_swap` | ✅ | ✅ | Supported |
| `timeloop` | ✅ | ✅ | Supported |
| `timestring` | ✅ | ✅ | Supported |
| `twotone` | ✅ | ✅ | Supported |
| `vectorangle` | ✅ | ✅ | Supported |
| `vectorlength` | ✅ | ✅ | Supported |
| `vectorx` | ✅ | ✅ | Supported |
| `vectory` | ✅ | ✅ | Supported |
| `weighted_average` | ✅ | ✅ | Supported |
| `wplist` | ✅ | ✅ | Supported |

</details>

---

## 5. Coverage Regression Gate

The coverage matrix is enforced in CI via `server/tests/unit/test_coverage_matrix.py`.
Any modification to Synfig MCP or tool definitions that lowers the count of supported layers or parameters will cause CI to fail.
