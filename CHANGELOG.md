# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-03

### Added
- Initial public release of `synfig-mcp`.
- **System tools**: `synfig_doctor`, `synfig_version`, `list_render_targets`, `list_layer_types`.
- **Project tools**: `create_project`, `open_project`, `save_project`, `save_project_as`, `close_project`, `list_open_projects`, `get_project_info`, `set_canvas_properties`, `set_time_range`, `set_fps`, `set_image_span`, `duplicate_project`, `validate_project`.
- **Layer tools**: `add_layer`, `delete_layer`, `duplicate_layer`, `move_layer`, `rename_layer`, `set_layer_param`, `get_layer_param`, `list_layers`, `get_layer`, `enable_layer`, `disable_layer`, `set_blend_method`, `set_amount`, `set_z_depth`, `group_layers`, `ungroup_layers`, `lock_layer`, `exclude_from_rendering`.
- **Shape tools**: `add_circle`, `add_rectangle`, `add_polygon`, `add_star`, `add_outline`, `add_advanced_outline`, `add_region`, `add_text`, `add_gradient`, `add_image`, `add_solid_color`, `add_checkerboard`, `add_noise_gradient`, `add_bline`.
- **Filter tools**: `add_blur`, `add_motion_blur`, `add_color_correct`, `add_halftone`, `add_clamp`, `add_stretch`, `add_rotate`, `add_translate`, `add_zoom`, `add_twirl`, `add_bevel`, `add_shade`, `add_radial_blur`, `add_distortions`, `add_duplicate`.
- **Animation tools**: `animate_param`, `add_waypoint`, `remove_waypoint`, `set_interpolation`, `add_keyframe`, `remove_keyframe`, `move_keyframe`, `list_keyframes`, `set_time_loop`, `convert_param`, `add_time_offset`, `bake_animation`.
- **Skeleton & bones**: `export_value`, `link_params`, `unlink_params`, `create_bone`, `bind_skeleton`, `list_bones`, `set_bone_param`.
- **Asset tools**: `import_asset`, `list_assets`, `embed_image`, `set_canvas_inline`, `import_svg`.
- **Render & export**: `render_frame`, `render_animation`, `render_preview`, `render_thumbnail`, `get_render_status`, `cancel_render`.
- **Batch & utility**: `batch_operations`, `undo`, `redo`, `diff_projects`, `export_json_snapshot`, `import_json_snapshot`, `apply_template`.
- **MCP Resources**: `synfig://projects`, `synfig://project/{id}/info`, `synfig://project/{id}/layers`, `synfig://project/{id}/xml`, `synfig://docs/layer-types`.
- **MCP Prompts**: `create_logo_animation`, `create_explainer_scene`, `rig_character`, `loop_gif`, `fix_broken_project`.
- Comprehensive test suite with 560+ tests and >90% coverage.
