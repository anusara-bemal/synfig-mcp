# Effects Recipes & Style Presets Guide

`synfig-mcp` includes a comprehensive library of parameterized visual effect recipes and aesthetic style presets designed for 2D animation, anime-style action sequences, motion graphics, and post-processing.

Every recipe is composed entirely from Synfig's native layer graph (`noise`, `radial_blur`, `colorcorrect`, `shade`, `curve_warp`, `bevel`, `halftone2`, `motion_blur`, etc.) and applies as a **single atomic undo step** via `scene_build`.

---

## 1. Effects Recipe Library

The library provides 14 composable effect recipes accessible via the `fx` and `all` tool profiles:

| Recipe Name | Category | Primary Layers Composed | Description |
|---|---|---|---|
| `speed_lines` | action | `linear_gradient`, `noise`, `clamp` | Dynamic radial or directional action speed lines with configurable density and contrast. |
| `radial_blur_burst` | action | `radial_blur`, `colorcorrect` | Impact-triggered zoom/radial blur burst centered on a focal point. |
| `impact_frame` | action | `solid_color`, `invert`, `colorcorrect` | Inverted high-contrast monochrome flash frame for high-impact hits or explosions. |
| `slash_arc` | action | `advanced_outline`, `radial_blur`, `glow` | Curved glowing weapon or speed slash arc with trailing fade. |
| `energy_aura` | action | `noise_distort`, `radial_blur`, `solid_color` | Flowing noise-driven energy aura or flame distortion surrounding a character. |
| `vignette` | post | `radial_gradient`, `colorcorrect` | Subtle edge darkening / vignette to guide viewer focus toward screen center. |
| `film_grain` | post | `noise`, `blend_method:overlay` | Organic animated or static analog film grain overlay. |
| `chromatic_aberration` | post | `colorcorrect`, `translate` | Optical lens fringe split separating red, green, and blue color channels. |
| `camera_shake` | camera | `translate`, `rotate` | Procedural or damped camera rumble for hits, earthquakes, and footsteps. |
| `halftone_screentone` | style | `halftone2`, `colorcorrect` | Retro manga/comic-book dot screentone pattern with adjustable angle and frequency. |
| `cel_shade_rim` | compositing | `shade`, `colorcorrect` | Sharp cel-shaded contour shadows and luminous rim light highlights. |
| `color_grade_stack` | color | `colorcorrect`, `solid_color` | Comprehensive color grade with gamma, saturation, hue shift, and shadow/highlight tints. |
| `limited_animation_timing` | timing | `time_loop` | Quantizes keyframe playback to anime-style "on twos" (12fps) or "on threes" (8fps). |
| `transition_whip_pan` | transition | `motion_blur`, `translate` | Fast directional whip pan transition with motion streaking between scene cuts. |

### Recipe Usage via MCP Tools

```json
// List all registered recipes
recipe_list()

// Get full parameter schema and details for a recipe
recipe_info(name="speed_lines")

// Apply recipe to canvas at specific time
recipe_apply(
  name="speed_lines",
  params={
    "density": 18,
    "contrast": 1.6,
    "angle_deg": 45.0,
    "origin_x": 0.0,
    "origin_y": 0.0
  },
  target="0s"
)
```

---

## 2. Style Presets

Style presets apply global aesthetic palettes, post-processing stacks, and animation timing rules across a scene:

### 1. `shonen_action`
- **Theme**: High-octane action sequence, punchy impact timing.
- **Timing**: Limited animation on threes (8fps) with dynamic hold frames.
- **Palette**: Deep blacks (`#0B0C10`), stark white highlights, saturated crimson/gold energy accents.
- **Effects Stack**: `speed_lines`, `radial_blur_burst`, `impact_frame`, `vignette`.

### 2. `dark_fantasy`
- **Theme**: Moody, atmospheric, low-key lighting.
- **Timing**: Standard 24fps with smooth easing.
- **Palette**: Desaturated charcoal (`#1A1A24`), muted olive, pale bone white, cold teal highlights.
- **Effects Stack**: `cel_shade_rim`, `film_grain`, `vignette`, `color_grade_stack`.

### 3. `supernatural_noir`
- **Theme**: Stark monochrome contrast with isolated color accents.
- **Timing**: Limited animation on twos (12fps).
- **Palette**: Pure black (`#000000`), stark white (`#FFFFFF`), selective spot crimson (`#E63946`).
- **Effects Stack**: `halftone_screentone`, `vignette`, `color_grade_stack`.

### 4. `cyber_mecha`
- **Theme**: High-tech sci-fi, sharp vector geometry, optical lens artifacts.
- **Timing**: Crisp 24fps mechanical animation.
- **Palette**: Dark steel navy (`#0A1128`), electric cyan (`#00F5D4`), fluorescent magenta (`#F72585`).
- **Effects Stack**: `chromatic_aberration`, `film_grain`, `energy_aura`.

### 5. `retro_anime`
- **Theme**: 1980s/1990s cel-shaded aesthetic on warm film stock.
- **Timing**: Animation on twos (12fps).
- **Palette**: Cream paper whites (`#FFFDF0`), soft sepia undertones, warm pastels.
- **Effects Stack**: `film_grain`, `chromatic_aberration`, `halftone_screentone`, `color_grade_stack`.

### Applying Style Presets via MCP Tools

```json
// List all style presets
style_list()

// Inspect a style preset
style_get(name="cyber_mecha")

// Apply style preset to active document
style_apply(name="cyber_mecha", time="0s")
```
