# Cut-Out Character Rig & Storyboard Animatic Example

> **Phase A4 Example Project** (Target: v0.8.0-rc1)

## Overview
This project demonstrates creating a 2D cut-out character puppet and a multi-shot animatic sequence built **entirely from 100% original Synfig vector geometry** (no third-party or copyrighted assets).

### Contents
- `character_spec.json`: Declarative specification of anatomical puppet parts (head, torso, limbs) with pivot origins and forward-kinematic bone hierarchy.
- `storyboard_script.json`: 3-shot scripted animatic timeline with shot descriptions, camera pans, and dialogue cues.
- `generate_example.py`: Autonomous generator script assembling the storyboard, character rig, keyframe poses, and effects stack.

### Running
```bash
python examples/cutout_character_animatic/generate_example.py
```
Output SIF project is generated atomically in one pass.
