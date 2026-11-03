# Synfig Document Format (.sif, .sifz, .sfg) Notes

## Overview

Synfig Studio uses an XML-based document architecture. Understanding its structure allows `synfig-mcp` to manipulate projects losslessly.

## File Formats

1. **`.sif` (Synfig XML Document)**
   - Plain UTF-8 XML document.
   - Root element is `<canvas>`.
   - Ideal for inspection, diffing, and version control.

2. **`.sifz` (Gzip-compressed XML)**
   - Standard gzip compression wrapping a `.sif` XML stream.
   - Default save format in modern Synfig Studio to minimize file size.

3. **`.sfg` (Synfig Package Container)**
   - Standard ZIP archive containing:
     - `project.sifz` or `project.sif`: The main animation canvas.
     - `images/`, `sounds/`, `media/`: Embedded external assets.

## Canvas Structure

A canvas root tag defines document-level properties:

```xml
<canvas version="1.0"
        width="1920"
        height="1080"
        xres="2834.645910"
        yres="2834.645910"
        view-box="-4.000000 2.250000 4.000000 -2.250000"
        antialias="1"
        fps="24.000"
        begin-time="0f"
        end-time="5s 0f"
        bgcolor="0.500000 0.500000 0.500000 1.000000">
  <name>Project Title</name>
  <defs>
    <!-- Exported parameters, shared value nodes, skeletons -->
  </defs>
  <!-- Layers rendered bottom-to-top (index 0 is bottom/background) -->
  <layer type="solid_color" active="true" version="0.1" desc="Background">
    ...
  </layer>
  <layer type="circle" active="true" version="0.1" desc="Ball">
    ...
  </layer>
</canvas>
```

### Coordinate Space & Units

- **Canvas Units**: Synfig uses a Cartesian coordinate space where `(0, 0)` is the center of the canvas.
  - `+X` points right.
  - `+Y` points UP (unlike standard screen/web pixels where +Y is down).
- **Pixel conversion**: By default, Synfig maps 60 pixels to 1 canvas unit (`SYNFIG_MCP_UNIT_PX = 60.0`).
- **Aspect Ratio**: Handled via `view-box="min_x max_y max_x min_y"`.

### Layer Definitions

Layers wrap their visual settings in `<param>` tags:

```xml
<layer type="circle" active="true" version="0.2" desc="Circle Layer">
  <param name="z_depth"><real value="0.0000000000"/></param>
  <param name="amount"><real value="1.0000000000"/></param>
  <param name="blend_method"><integer value="0"/></param>
  <param name="color">
    <color>
      <r>1.000000</r>
      <g>0.200000</g>
      <b>0.100000</b>
      <a>1.000000</a>
    </color>
  </param>
  <param name="radius"><real value="1.5000000000"/></param>
  <param name="origin">
    <vector>
      <x>0.0000000000</x>
      <y>0.0000000000</y>
    </vector>
  </param>
</layer>
```

### Parameter Animation & Waypoints

Animated parameters replace the static value tag with `<animated>` containing `<waypoint>` elements:

```xml
<param name="origin">
  <animated type="vector">
    <waypoint time="0s" before="clamped" after="clamped">
      <vector>
        <x>-2.0000000000</x>
        <y>0.0000000000</y>
      </vector>
    </waypoint>
    <waypoint time="2s" before="clamped" after="clamped">
      <vector>
        <x>2.0000000000</x>
        <y>1.5000000000</y>
      </vector>
    </waypoint>
  </animated>
</param>
```

Interpolation types for `before` and `after`:
- `clamped`: Smooth easing preventing overshoot.
- `tcb`: Tension-Continuity-Bias spline interpolation.
- `constant`: Step/hold value until next waypoint.
- `ease`: Classic ease-in / ease-out curves.
- `linear`: Constant rate of change between points.

### Exported Values & Linking

Parameters can be linked across layers by moving the value definition into `<defs>` and referencing it with `use=":<name>"`:

```xml
<defs>
  <vector id="shared_position">
    <x>0.000000</x>
    <y>1.000000</y>
  </vector>
</defs>
...
<param name="origin" use=":shared_position"/>
```
