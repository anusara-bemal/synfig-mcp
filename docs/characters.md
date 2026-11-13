# Rig sheet to animated scene

Three calls take a character sheet and a background to a moving shot.

1. `rig_sheet_slice(file_path)` - finds every part on the sheet and returns a numbered
   preview. Look at `preview_base64` and decide what each number is. Each part already
   carries its rig metadata (role, parent, pivot, z), a confidence score and a
   `rig_compatibility` report; enclosed gaps are reconstructed best-effort.
2. `rig_sheet_slice(file_path, names={"1": "head", "2": "torso", ...})` - writes one
   transparent PNG per named part and a `manifest.json`. Unnamed numbers (captions,
   stray marks) are left out.
3. `scene_auto_build(spec)` - builds everything in one undo step:

```json
{
  "width": 1920, "height": 1080, "fps": 24, "duration": 6,
  "background": {"file": "bg.png"},
  "characters": [{
    "id": "hero", "manifest": "sheet_parts/manifest.json",
    "position": {"x": 300, "y": 950}, "height": 600,
    "actions": [
      {"motion": "walk", "start": 0, "end": 4, "move_to": {"x": 1400, "y": 950}},
      {"motion": "wave", "start": 4}
    ]
  }],
  "camera": [{"time": 0, "zoom": 1}, {"time": 6, "zoom": 1.3, "center": {"x": 1400, "y": 600}}],
  "save_path": "shot_01.sif"
}
```

## Naming parts
Parts named by body role get their joints and hierarchy automatically:
`torso` (root), `head`, `neck`, `hips`, `upper_arm_l/r`, `forearm_l/r`, `hand_l/r`,
`upper_leg_l/r`, `lower_leg_l/r`, `foot_l/r`, or single-piece `arm_l/r`, `leg_l/r`.
`_l` limbs are drawn behind the torso, `_r` limbs in front. Anything else (hair, tail,
sword) needs `parent` and `attach`.

## Fixing joints
The defaults are estimates. Look at the preview, then override per part:
- `pivot: {fx, fy}` - the joint inside the part image (0,0 = top-left, 1,1 = bottom-right).
- `attach: {fx, fy}` - where that joint sits on the parent image.
- `z` - stacking inside the parent: negative is behind the parent art.
- `layout: "in_place"` keeps the sheet positions (for parts exported in place).

## Animating
- Motions: walk, run, idle, talk (loop), wave, jump, nod, punch (once), rest, pose, move.
- Angles are degrees from the rest pose, counter-clockwise; `flip: true` mirrors a character.
- `character_motion_apply` and `character_pose_apply(angles={"upper_arm_r": 120})` refine a
  built character; the joint layers are `<id>_<part>_rot`, the position layer `<id>_pos`.
- Check the result with `review_sequence`, export with `render_video`.

## Limits
- Joints are rotate layers (forward kinematics); there is no IK, mesh deformation or lip-sync.
- Without `doc_id` a new document is created; pass `doc_id` to build into the open one.

## What is verified

- The slicing, the rig geometry, the motion planner and the tool flow are covered by
  `test_rig_sheet.py`, `test_cutout_rig.py` and `test_scene_auto_build.py` on both backends.
- `test_auto_built_character_scene_loads_and_moves` loads and renders the built scene with
  the real Synfig engine in CI.
- The live path uses the same `scene.build` request as every other declarative build; it has
  not been exercised against a real Studio session for this feature yet.
