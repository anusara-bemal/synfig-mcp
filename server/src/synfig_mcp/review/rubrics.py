"""
Vision critique rubrics and checklist resources for the Visual Review Loop.
Accessible via MCP resources: synfig://rubrics/{style}.
Strict IP policy: generic, neutral names only (no franchise names).
"""

from __future__ import annotations

RUBRICS: dict[str, str] = {
    "shonen_action": """# Visual Review Rubric: Shonen Action

## Key Aesthetic Traits
- High dynamic range and dramatic directional lighting.
- Crisp line weight with bold outer contours.
- High-contrast impact frames (single-frame flashes or inverted silhouettes).
- Dynamic diagonal camera compositions emphasizing momentum.

## Vision Model Checklist
1. **Speed Lines**: Are radial or directional blur lines aligned with the focal object's motion vector?
2. **Impact Frames**: Does the point of maximum force exhibit adequate contrast and a hold frame?
3. **Motion Trajectory**: Are action arcs smooth without jitter between adjacent keyframes?
4. **Safe Area**: Do key explosive elements avoid being abruptly cut off at outer canvas borders?
5. **Readability**: Is the hero subject clearly silhouetted against the background?
""",
    "dark_fantasy": """# Visual Review Rubric: Dark Fantasy

## Key Aesthetic Traits
- Crushed midtones and atmospheric shadows.
- Desaturated earth tones accented by vivid supernatural glows.
- Strong rim lighting separating characters from dense backgrounds.
- Subtle vignette and film grain texture.

## Vision Model Checklist
1. **Luminance Balance**: Are shadows deep without completely crushing character silhouettes?
2. **Rim Lighting**: Is the rim light consistent with active scene light sources (fire, magic, moon)?
3. **Palette Cohesion**: Are accent colors restrained and intentional?
4. **Atmosphere**: Do fog, mist, or particle distortion layers integrate naturally with camera depth?
""",
    "supernatural_noir": """# Visual Review Rubric: Supernatural Noir

## Key Aesthetic Traits
- High-contrast chiaroscuro lighting (hard shadows, sharp edge falloff).
- Predominantly monochrome or duotone palette with targeted chromatic punches.
- Deep silhouette framing and expressive negative space.

## Vision Model Checklist
1. **Negative Space**: Does the shadow composition direct the viewer's eye to the narrative focal point?
2. **Edge Definition**: Are hard shadows crisp without unintended anti-aliasing artifacts?
3. **Color Accents**: If an accent color is used (e.g. crimson or ethereal cyan), is it legible and deliberate?
""",
    "cinematic": """# Visual Review Rubric: Cinematic Animation

## Key Aesthetic Traits
- Rule-of-thirds framing and standard 2.39:1 / 16:9 aspect ratio balance.
- Action Safe (90%) and Title Safe (80%) SMPTE compliance.
- Depth of field (foreground blur, sharp subject, soft background).
- Balanced color grading with consistent exposure across cuts.

## Vision Model Checklist
1. **Safe Areas**: Are all textual titles and critical narrative elements inside Title Safe (80%)?
2. **Depth Layering**: Are foreground, midground, and background separated with appropriate parallax?
3. **Exposure**: Are highlights clean with no unintentional over-exposure clipping?
4. **Camera Movement**: Is pan/tilt easing natural (smooth acceleration and deceleration)?
""",
    "general": """# Visual Review Rubric: General Animation Standards

## Basic Quality Checklist
1. **Canvas Coverage**: Ensure scene is not accidentally transparent or rendering a blank background.
2. **Luminance Bounds**: Check that luminance does not clip at pure 0.0 or pure 1.0 uncontrollably.
3. **Strobe Risk**: Ensure rapid full-screen flashes do not exceed photosensitivity safety limits (WCAG 2.3.1).
4. **Aspect & Framing**: Ensure characters and props are well-proportioned within the composition.
5. **Frame-to-Frame Continuity**: Confirm that transitions between keyframes are smooth and intentional.
""",
}


def get_rubric(style: str) -> str:
    """Retrieve visual critique rubric by style name, falling back to general rubric."""
    normalized = style.lower().strip()
    return RUBRICS.get(normalized, RUBRICS["general"])


def list_available_rubrics() -> list[str]:
    """Return available rubric style names."""
    return sorted(RUBRICS.keys())
