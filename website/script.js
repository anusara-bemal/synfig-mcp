/**
 * Synfig MCP Website — Interactive Developer Experience
 * Vanilla JS · Zero External Libraries · Zero Runtime Deps
 */

// ============================================================
// 81 Synfig MCP Tool Catalog
// ============================================================
const TOOLS_CATALOG = [
  // CORE (13)
  { name: "health_check",       profile: "core",   desc: "Verifies server connectivity, active backend (live vs headless), and Synfig runtime status.",                                        params: "()" },
  { name: "synfig_help",        profile: "core",   desc: "Authoritative syntax, documentation, parameter types, and schema guidance for requested topics.",                                     params: "(topic: string)" },
  { name: "doc_new",            profile: "core",   desc: "Creates a new animation canvas document with width, height, fps, and metadata.",                                                     params: "(width?, height?, fps?, name?)" },
  { name: "doc_open",           profile: "core",   desc: "Opens an existing .sif, .sifz, or .sfg document within the security sandbox.",                                                       params: "(file_path: string)" },
  { name: "doc_save",           profile: "core",   desc: "Saves active animation document atomically to disk.",                                                                                params: "(file_path?: string)" },
  { name: "doc_info",           profile: "core",   desc: "Inspects canvas dimensions, frame rate, timeline boundaries, and layer hierarchy.",                                                  params: "()" },
  { name: "scene_build",        profile: "core",   desc: "Primary construction tool. Builds layers, hierarchies, parameters, and waypoints in 1 atomic undo step.",                           params: "(spec: object, dry_run?: bool)" },
  { name: "scene_export_spec",  profile: "core",   desc: "Serializes active canvas layers and keyframes into compact JSON scene spec.",                                                        params: "(scope?, fields?)" },
  { name: "scene_summary",      profile: "core",   desc: "Hierarchical overview of canvas with token-budget truncation.",                                                                      params: "(budget_tokens?: int)" },
  { name: "history_undo",       profile: "core",   desc: "Rolls back the last studio action on the GTK main thread.",                                                                         params: "()" },
  { name: "history_redo",       profile: "core",   desc: "Reapplies the previously undone action on the GTK main thread.",                                                                    params: "()" },
  { name: "render_frame",       profile: "core",   desc: "Renders single frame to lossless PNG preview with base64 return.",                                                                  params: "(time?, width?, height?, quality?)" },
  { name: "schema_introspect",  profile: "core",   desc: "Schema reflection for layer types, value nodes, and render targets.",                                                               params: "(entity_type: string)" },

  // ANIM (21)
  { name: "anim_keyframe_add",       profile: "anim", desc: "Adds a timeline keyframe bookmark at specified time with description.",                                            params: "(time: string, description?: string)" },
  { name: "anim_keyframe_list",      profile: "anim", desc: "Lists all keyframes in active document with timecodes and descriptions.",                                          params: "()" },
  { name: "anim_keyframe_remove",    profile: "anim", desc: "Removes a keyframe at specified time position.",                                                                   params: "(time: string)" },
  { name: "anim_waypoint_set",       profile: "anim", desc: "Creates or updates parameter waypoint with easing (clamped, smooth, linear, constant).",                          params: "(layer, param, time, value, interp?)" },
  { name: "anim_waypoint_remove",    profile: "anim", desc: "Deletes a parameter waypoint at specified timecode.",                                                              params: "(layer, param, time)" },
  { name: "anim_animate_param",      profile: "anim", desc: "Batch creates an entire sequence of interpolated waypoints for a parameter.",                                      params: "(layer, param, waypoints: array)" },
  { name: "anim_time_get",           profile: "anim", desc: "Returns current playhead time position in document.",                                                              params: "()" },
  { name: "anim_time_set",           profile: "anim", desc: "Scrubs timeline playhead to specific frame or timestamp.",                                                         params: "(time: string)" },
  { name: "anim_interpolation_set",  profile: "anim", desc: "Sets default interpolation mode (TCB, linear, ease-in, ease-out, constant).",                                     params: "(layer, param, interpolation)" },
  { name: "doc_set_time_range",      profile: "anim", desc: "Configures start time, end time, and loop boundaries for canvas.",                                                 params: "(start_time, end_time)" },
  { name: "param_get",               profile: "anim", desc: "Reads current or animated value of a layer parameter at current time.",                                            params: "(layer_name, param_name)" },
  { name: "param_set",               profile: "anim", desc: "Updates layer parameter value statically or in animation mode.",                                                   params: "(layer_name, param_name, value)" },
  { name: "param_convert",           profile: "anim", desc: "Converts parameter to procedural valuenode (add, scale, sine, timeloop, etc.).",                                   params: "(layer, param, valuenode_type)" },
  { name: "anim_loop_set",           profile: "anim", desc: "Configures looping behaviour on a parameter valuenode.",                                                           params: "(layer, param, loop_mode)" },
  { name: "anim_loop_get",           profile: "anim", desc: "Returns looping configuration for a parameter's valuenode.",                                                       params: "(layer, param)" },
  { name: "anim_speed_set",          profile: "anim", desc: "Scales all waypoint timings on a layer parameter by a speed factor.",                                              params: "(layer, param, factor: float)" },
  { name: "anim_curve_bake",         profile: "anim", desc: "Bakes a live animation curve into discrete per-frame waypoints for portability.",                                  params: "(layer, param, start_time, end_time, fps?)" },
  { name: "anim_retarget",           profile: "anim", desc: "Re-maps animation curves from one layer onto another target layer.",                                               params: "(source_layer, target_layer, params?)" },
  { name: "anim_timing_offset",      profile: "anim", desc: "Shifts all waypoints on a layer parameter by a time delta.",                                                       params: "(layer, param, delta: string)" },
  { name: "anim_ease_global",        profile: "anim", desc: "Applies a global ease-in/ease-out curve adjustment to all waypoints within a time range.",                         params: "(start_time, end_time, ease_in, ease_out)" },
  { name: "anim_snapshot",           profile: "anim", desc: "Captures current parameter state as a named snapshot for later restoration.",                                      params: "(name: string, layers?)" },

  // FX (25)
  { name: "layer_add",          profile: "fx", desc: "Instantiates a new primitive, shape, gradient, or filter layer into the document.",                   params: "(type: string, name?: string)" },
  { name: "layer_remove",       profile: "fx", desc: "Deletes specified layer from canvas hierarchy.",                                                      params: "(name: string)" },
  { name: "layer_duplicate",    profile: "fx", desc: "Duplicates a layer or group with linked or independent parameters.",                                  params: "(name: string)" },
  { name: "layer_group",        profile: "fx", desc: "Encapsulates collection of layers into hierarchically grouped switch/canvas layer.",                   params: "(layer_names, group_name)" },
  { name: "layer_ungroup",      profile: "fx", desc: "Flattens a group layer back into parent canvas.",                                                     params: "(group_name: string)" },
  { name: "layer_reorder",      profile: "fx", desc: "Reorders layer position in rendering Z-stack.",                                                       params: "(name: string, index: int)" },
  { name: "layer_rename",       profile: "fx", desc: "Renames a layer within the canvas.",                                                                  params: "(name: string, new_name: string)" },
  { name: "layer_visibility",   profile: "fx", desc: "Toggles layer visibility on the canvas.",                                                             params: "(name: string, visible: bool)" },
  { name: "layer_link_param",   profile: "fx", desc: "Dynamically links a parameter of one layer to another layer's parameter via shared valuenode.",        params: "(layer_a, param_a, layer_b, param_b)" },
  { name: "recipe_list",        profile: "fx", desc: "Lists all 14 built-in anime, cinematic, and motion graphics effect recipes.",                          params: "()" },
  { name: "recipe_info",        profile: "fx", desc: "Returns JSON schema and parameter requirements for a specific effect recipe.",                         params: "(name: string)" },
  { name: "recipe_apply",       profile: "fx", desc: "Applies an effect recipe (anime speedlines, halftone, glow) in 1 atomic undo step.",                  params: "(name, params?, target?)" },
  { name: "style_list",         profile: "fx", desc: "Lists available aesthetic color presets and palettes.",                                                params: "()" },
  { name: "style_apply",        profile: "fx", desc: "Applies full color grading and styling preset to canvas layers.",                                      params: "(name: string, time?: string)" },
  { name: "blend_mode_set",     profile: "fx", desc: "Sets layer compositing blend mode (Normal, Multiply, Screen, Overlay, etc.).",                        params: "(layer: string, mode: string)" },
  { name: "gradient_create",    profile: "fx", desc: "Creates a linear or radial gradient layer with specified color stops.",                               params: "(type, stops: array, name?)" },
  { name: "noise_layer_add",    profile: "fx", desc: "Adds procedural noise layer (perlin, simplex, worley) with configurable frequency.",                   params: "(type, frequency, amplitude)" },
  { name: "distort_warp",       profile: "fx", desc: "Applies a warp distortion effect layer to specified target layers.",                                   params: "(target, warp_type, amount)" },
  { name: "blur_add",           profile: "fx", desc: "Adds a blur layer (box, gaussian, motion, radial) with specified parameters.",                         params: "(type, size, target?)" },
  { name: "mask_layer_add",     profile: "fx", desc: "Creates a bitmap or vector mask layer linked to a target.",                                            params: "(target_layer, mask_type)" },
  { name: "outline_add",        profile: "fx", desc: "Adds a stroked outline layer to any spline or region layer.",                                          params: "(target_layer, width, color?)" },
  { name: "shadow_add",         profile: "fx", desc: "Adds a drop shadow composite effect to a layer group.",                                               params: "(target_layer, offset, blur, color?)" },
  { name: "particle_system_add",profile: "fx", desc: "Creates a particle emitter layer with configurable spawn rate, lifetime, and physics.",               params: "(name, emitter_spec: object)" },
  { name: "fx_chain_apply",     profile: "fx", desc: "Applies a named sequence of effects as a single undo-able operation.",                                 params: "(chain_name: string, target?)" },
  { name: "canvas_resize",      profile: "fx", desc: "Resizes or crops the canvas with optional anchor alignment and layer scaling.",                        params: "(width, height, anchor?, scale_layers?)" },

  // RIG (23)
  { name: "bone_create",              profile: "rig", desc: "Creates an individual bone in the skeleton layer with length, tip, and angle.",                                      params: "(skeleton_layer, name, origin, length)" },
  { name: "bone_link_parent",         profile: "rig", desc: "Establishes hierarchical parent-child relationship between two bones.",                                              params: "(child_bone, parent_bone)" },
  { name: "bone_transform_set",       profile: "rig", desc: "Rotates, translates, or scales a bone at a specific timeline position.",                                            params: "(bone_name, origin, angle, length)" },
  { name: "bone_delete",              profile: "rig", desc: "Removes a bone and optionally re-parents its children.",                                                            params: "(bone_name, reparent?: bool)" },
  { name: "bone_rename",              profile: "rig", desc: "Renames an existing bone within a skeleton layer.",                                                                  params: "(skeleton_layer, old_name, new_name)" },
  { name: "bone_weight_set",          profile: "rig", desc: "Sets influence weight of a bone on a linked deformable layer.",                                                     params: "(bone_name, target_layer, weight)" },
  { name: "skeleton_create",          profile: "rig", desc: "Creates a new skeleton layer in the canvas.",                                                                       params: "(name: string, position?)" },
  { name: "skeleton_distortion_add",  profile: "rig", desc: "Applies a Skeleton Distortion deformer layer to smoothly bend bitmap graphics.",                                    params: "(target_layer, skeleton_name)" },
  { name: "character_rig_from_parts", profile: "rig", desc: "Constructs complete bone skeleton and binds anatomical SVG/PNG parts automatically.",                               params: "(spec: object)" },
  { name: "character_pose_apply",     profile: "rig", desc: "Applies a predefined character keyframe pose (idle, walk, run, jump, punch).",                                      params: "(character_name, pose_name, time?)" },
  { name: "character_pose_save",      profile: "rig", desc: "Saves current bone transforms as a named reusable pose.",                                                           params: "(character_name, pose_name)" },
  { name: "ik_solve",                 profile: "rig", desc: "Runs inverse kinematics solver to position a bone chain's end effector.",                                          params: "(end_bone, target_position, iterations?)" },
  { name: "ik_constraint_add",        profile: "rig", desc: "Adds a constraint (look-at, limit angle, two-bone IK) to a bone.",                                                 params: "(bone_name, constraint_type, params: object)" },
  { name: "deformer_warp_add",        profile: "rig", desc: "Adds a warp-pin or curve deformer linked to skeleton motion.",                                                     params: "(target_layer, deformer_type)" },
  { name: "bind_region_to_bone",      profile: "rig", desc: "Binds a vector region layer to follow a skeleton bone.",                                                           params: "(region_layer, bone_name, weight?)" },
  { name: "bind_spline_to_bone",      profile: "rig", desc: "Links a spline layer's control points to skeleton bone transforms.",                                               params: "(spline_layer, bone_name)" },
  { name: "rig_symmetry_mirror",      profile: "rig", desc: "Mirrors bone hierarchy and weights from one side to another (L/R).",                                               params: "(skeleton_layer, axis)" },
  { name: "rig_export_bvh",           profile: "rig", desc: "Exports skeleton animation to BVH motion capture format.",                                                         params: "(output_path, start_time, end_time)" },
  { name: "control_rig_add",          profile: "rig", desc: "Adds a simplified control rig over the deform skeleton for animator-friendly IK handles.",                         params: "(character_name, control_spec: object)" },
  { name: "blend_shape_add",          profile: "rig", desc: "Adds a blend shape (morph target) driven by a named parameter.",                                                   params: "(target_layer, shape_name, driver_param)" },
  { name: "cloth_sim_add",            profile: "rig", desc: "Attaches a simple cloth physics simulation to a bone chain.",                                                      params: "(bone_chain, stiffness, damping)" },
  { name: "squash_stretch_rig",       profile: "rig", desc: "Auto-rigs a squash and stretch control network for a character limb.",                                             params: "(limb_bone, controller_name)" },
  { name: "rig_validate",             profile: "rig", desc: "Validates rig integrity: checks for unbound bones, broken links, and weight normalization.",                       params: "(skeleton_layer)" },

  // ASSETS (12)
  { name: "asset_search",        profile: "assets", desc: "Searches vetted open-source permissive CC0/MIT asset repositories for vectors and audio.",       params: "(query: string, license?: string)" },
  { name: "asset_preview",       profile: "assets", desc: "Retrieves low-res thumbnail and metadata for an asset before downloading.",                       params: "(asset_id: string)" },
  { name: "asset_download",      profile: "assets", desc: "Hardened download with SSRF protection, size limits, and checksum validation.",                   params: "(url: string, local_name: string)" },
  { name: "asset_import_svg",    profile: "assets", desc: "Sanitizes and imports SVG vector artwork directly into Synfig vector spline layers.",             params: "(file_path: string)" },
  { name: "asset_import_image",  profile: "assets", desc: "Imports PNG/JPEG bitmap image and anchors onto canvas.",                                          params: "(file_path: string)" },
  { name: "asset_import_audio",  profile: "assets", desc: "Imports an audio file as a sound layer for lip sync and timing reference.",                      params: "(file_path: string, start_time?)" },
  { name: "asset_palette_load",  profile: "assets", desc: "Loads a color palette from .gpl or .ase file into the canvas swatch table.",                     params: "(file_path: string)" },
  { name: "asset_export_frames", profile: "assets", desc: "Exports rendered frames to disk with configurable naming pattern and format.",                    params: "(output_dir, pattern?, format?)" },
  { name: "asset_export_svg",    profile: "assets", desc: "Exports active canvas vector layers as clean SVG file.",                                          params: "(output_path: string, time?)" },
  { name: "asset_list_workspace",profile: "assets", desc: "Lists all files in the current workspace sandbox directory.",                                     params: "(subdir?: string)" },
  { name: "asset_hash",          profile: "assets", desc: "Returns SHA-256 checksum for a file in the sandbox for integrity verification.",                  params: "(file_path: string)" },
  { name: "asset_cleanup",       profile: "assets", desc: "Removes unused or orphaned asset files from the workspace.",                                     params: "(dry_run?: bool)" },

  // REVIEW (18)
  { name: "review_ssim",           profile: "review", desc: "Calculates structural similarity index between rendered frame and reference image.",                 params: "(frame_a, frame_b)" },
  { name: "review_diff_heatmap",   profile: "review", desc: "Generates visual heatmap diff highlighting pixel deviations between two frames.",                   params: "(frame_a, frame_b)" },
  { name: "review_palette_audit",  profile: "review", desc: "Extracts dominant colors, checks contrast ratios, and flags out-of-gamut hues.",                   params: "(time?: string)" },
  { name: "review_safe_areas",     profile: "review", desc: "Audits composition against 16:9 Title Safe (80%) and Action Safe (90%) margins.",                  params: "(time?: string)" },
  { name: "review_strobe_check",   profile: "review", desc: "Analyzes luminance deltas across frame sequence to prevent photosensitive epilepsy risks.",         params: "(start_time, end_time)" },
  { name: "review_color_grade",    profile: "review", desc: "Applies automated color grading suggestions based on scene mood analysis.",                         params: "(mood?: string)" },
  { name: "review_motion_blur",    profile: "review", desc: "Analyzes motion vectors and suggests optimal motion blur parameters.",                              params: "(start_time, end_time)" },
  { name: "review_layer_audit",    profile: "review", desc: "Audits layer naming conventions, group structure, and documentation completeness.",                 params: "()" },
  { name: "render_sequence",       profile: "review", desc: "Renders continuous sequence of frames to disk with progress reporting.",                            params: "(start_time, end_time, output_dir)" },
  { name: "render_video",          profile: "review", desc: "Encodes rendered frames into MP4/WebM video via Synfig CLI and ffmpeg.",                           params: "(output_path, fps?, bitrate?)" },
  { name: "render_contact_sheet",  profile: "review", desc: "Generates multi-frame thumbnail grid contact sheet for rapid timeline review.",                     params: "(frame_count?: int)" },
  { name: "render_lottie",         profile: "review", desc: "Exports animation as Lottie JSON for web and mobile playback.",                                    params: "(output_path: string)" },
  { name: "review_benchmark",      profile: "review", desc: "Benchmarks render performance across different quality settings and reports timing stats.",          params: "(frame_count?, quality_levels?)" },
  { name: "review_accessibility",  profile: "review", desc: "Checks animation for accessibility issues: flash frequency, color contrast, motion intensity.",     params: "(start_time, end_time)" },
  { name: "review_compare_takes",  profile: "review", desc: "Side-by-side SSIM comparison of multiple animation takes or versions.",                             params: "(takes: array)" },
  { name: "review_export_report",  profile: "review", desc: "Generates a full QA report as JSON or HTML summarizing all review checks.",                        params: "(output_path: string, format?)" },
  { name: "review_timeline_gaps",  profile: "review", desc: "Detects gaps in keyframe coverage or un-animated parameters over a time range.",                   params: "(start_time, end_time)" },
  { name: "review_scene_stats",    profile: "review", desc: "Returns statistical overview of scene complexity: layer count, waypoints, bones, and render time.", params: "()" }
];

// ============================================================
// Bootstrap
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  initOSSelector();
  initClientConfigTabs();
  initCopyButtons();
  initToolsCatalog();
  initMobileMenu();
  initScrollSpy();
  initSimulationLoop();
});

// ============================================================
// OS Selector in Installation Wizard
// ============================================================
function initOSSelector() {
  const osBtns   = document.querySelectorAll(".os-btn");
  const osPanels = document.querySelectorAll(".os-content");

  osBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      const os = btn.dataset.os;

      osBtns.forEach(b => b.classList.remove("active"));
      osPanels.forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const panel = document.getElementById(`panel-${os}`);
      if (panel) panel.classList.add("active");
    });
  });
}

// ============================================================
// MCP Client Config Tabs
// ============================================================
function initClientConfigTabs() {
  const tabs   = document.querySelectorAll(".client-tab");
  const panels = document.querySelectorAll(".client-panel");

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const client = tab.dataset.client;

      tabs.forEach(t => t.classList.remove("active"));
      panels.forEach(p => p.classList.remove("active"));

      tab.classList.add("active");
      const panel = document.getElementById(`tab-${client}`);
      if (panel) panel.classList.add("active");
    });
  });
}

// ============================================================
// One-Click Copy Buttons
// ============================================================
function initCopyButtons() {
  document.addEventListener("click", e => {
    const btn = e.target.closest(".copy-btn, .copy-code-btn");
    if (!btn) return;

    let text = "";
    const targetId = btn.dataset.copyTarget;

    if (targetId) {
      const el = document.getElementById(targetId);
      if (el) text = el.innerText;
    } else {
      text = btn.dataset.copyText || "";
    }

    if (!text) return;

    navigator.clipboard.writeText(text).then(() => {
      const isCopyBtn = btn.classList.contains("copy-btn");
      if (isCopyBtn) {
        const orig = btn.innerText;
        btn.innerText = "✓ Copied!";
        btn.style.backgroundColor = "#10b981";
        btn.style.color = "#ffffff";
        btn.style.borderColor = "#10b981";
        setTimeout(() => {
          btn.innerText = orig;
          btn.style.backgroundColor = "";
          btn.style.color = "";
          btn.style.borderColor = "";
        }, 2000);
      } else {
        // Icon button (copy-code-btn)
        const origInner = btn.innerHTML;
        btn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#10b981" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>`;
        setTimeout(() => { btn.innerHTML = origInner; }, 2000);
      }
    }).catch(() => {
      // Fallback for non-secure contexts
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    });
  });
}

// ============================================================
// Tools Catalog — Render + Filter + Search
// ============================================================
function initToolsCatalog() {
  const grid        = document.getElementById("tools-cards-grid");
  const searchInput = document.getElementById("tool-search-input");
  const profileBtns = document.querySelectorAll(".profile-filter-btn");
  const countBadge  = document.getElementById("tools-count-badge");

  let currentProfile = "all";
  let currentSearch  = "";

  function render() {
    if (!grid) return;
    grid.innerHTML = "";

    const filtered = TOOLS_CATALOG.filter(tool => {
      const matchProfile = currentProfile === "all" || tool.profile === currentProfile;
      const q = currentSearch.toLowerCase();
      const matchSearch =
        tool.name.toLowerCase().includes(q) ||
        tool.desc.toLowerCase().includes(q) ||
        tool.params.toLowerCase().includes(q);
      return matchProfile && matchSearch;
    });

    if (countBadge) {
      countBadge.textContent = `${filtered.length} Tools`;
    }

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;padding:40px;text-align:center;color:var(--zinc-500);background:#fff;border:1px dashed var(--zinc-300);border-radius:8px;">
          No tools match <strong>"${escapeHtml(currentSearch)}"</strong>. Try a different keyword or select <strong>All</strong>.
        </div>`;
      return;
    }

    const fragment = document.createDocumentFragment();

    filtered.forEach(tool => {
      const card = document.createElement("div");
      card.className = "tool-item-card";
      card.innerHTML = `
        <div>
          <div class="tool-card-head">
            <span class="tool-fn-name">${escapeHtml(tool.name)}</span>
            <span class="tool-category-badge">${escapeHtml(tool.profile)}</span>
          </div>
          <p class="tool-card-desc">${escapeHtml(tool.desc)}</p>
        </div>
        <div class="tool-fn-signature">${escapeHtml(tool.params)}</div>`;
      fragment.appendChild(card);
    });

    grid.appendChild(fragment);
  }

  if (searchInput) {
    searchInput.addEventListener("input", e => {
      currentSearch = e.target.value.trim();
      render();
    });
  }

  profileBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      profileBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentProfile = btn.dataset.profile;
      render();
    });
  });

  render();
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ============================================================
// Mobile Navigation Toggle
// ============================================================
function initMobileMenu() {
  const toggle = document.getElementById("mobile-menu-toggle");
  const panel  = document.getElementById("mobile-nav-panel");
  if (!toggle || !panel) return;

  toggle.addEventListener("click", () => {
    panel.classList.toggle("open");
    toggle.setAttribute("aria-expanded", panel.classList.contains("open").toString());
  });

  // Close on link click
  panel.querySelectorAll("a").forEach(link => {
    link.addEventListener("click", () => panel.classList.remove("open"));
  });

  // Close on outside click
  document.addEventListener("click", e => {
    if (!panel.contains(e.target) && !toggle.contains(e.target)) {
      panel.classList.remove("open");
    }
  });
}

// ============================================================
// Scroll Spy — highlight active nav link
// ============================================================
function initScrollSpy() {
  const sections = Array.from(document.querySelectorAll("section[id]"));
  const links    = document.querySelectorAll(".nav-link[href^='#']");

  if (!sections.length || !links.length) return;

  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const id = entry.target.getAttribute("id");
        links.forEach(link => {
          link.classList.toggle("active", link.getAttribute("href") === `#${id}`);
        });
      }
    });
  }, { rootMargin: "-30% 0px -60% 0px", threshold: 0 });

  sections.forEach(sec => observer.observe(sec));
}

// ============================================================
// AI Prompt Simulation Loop
// ============================================================
function initSimulationLoop() {
  const simText = document.getElementById("sim-prompt-text");
  const simLog  = document.getElementById("sim-exec-log");
  if (!simText || !simLog) return;

  const scenarios = [
    {
      prompt: "Create an animated bouncing rubber ball with squash and stretch over 24 frames, then render a preview.",
      log: `> tools/call: scene_build(spec={ layers: ["Circle_Ball", "Shadow_Oval"] })
< GTK PassiveGrouper: committed 2 vector layers, 1 undo step
> tools/call: anim_waypoint_set(layer="Circle_Ball", param="scale", time="00:00:00:12", val=[1.3, 0.7])
< GTK main thread: TCB tangent eased
> tools/call: render_frame(time="00:00:00:12")
< Frame rendered in 38ms (SSIM 0.9982 · Safe area OK)`
    },
    {
      prompt: "Rig a 5-bone cutout humanoid character from anatomical SVG layers and apply the 'walk' pose preset.",
      log: `> tools/call: character_rig_from_parts(character="Ranger", bones=5)
< Skeleton created: root -> spine -> neck -> arm_l, arm_r
> tools/call: character_pose_apply(character="Ranger", pose="walk_contact")
< Keyframes placed at 0f, 6f, 12f, 18f, 24f (loopable)
> tools/call: review_strobe_check(start="0f", end="24f")
< Safe: 0 strobe violations detected`
    },
    {
      prompt: "Add a cinematic anime speedlines recipe behind the character and grade colors with 'sunset_cinematic' style.",
      log: `> tools/call: recipe_apply(name="anime_speedlines", params={ density: 40 })
< Created RadialBlur + SplineParticleGroup behind character
> tools/call: style_apply(name="sunset_cinematic")
< Color valuenodes remapped (warm orange & deep violet)
> tools/call: doc_save()
< Lossless SIF saved atomically to disk`
    },
    {
      prompt: "Export the finished animation as a Lottie JSON file and run a full visual QA review report.",
      log: `> tools/call: render_lottie(output_path="dist/hero_anim.json")
< Lottie exported: 48 frames, 24fps, 142 KB
> tools/call: review_palette_audit()
< 6 dominant colors · All contrast ratios WCAG AA compliant
> tools/call: review_export_report(output_path="qa_report.html")
< QA report generated: 0 critical, 2 warnings`
    }
  ];

  let idx = 0;

  function cycle() {
    idx = (idx + 1) % scenarios.length;
    const sc = scenarios[idx];

    // Fade out
    simText.style.opacity = "0";
    simLog.style.opacity  = "0";

    setTimeout(() => {
      simText.textContent = `\u201c${sc.prompt}\u201d`;
      simLog.textContent  = sc.log;
      simText.style.opacity = "1";
      simLog.style.opacity  = "1";
    }, 300);
  }

  // Set initial transition
  simText.style.transition = "opacity 0.3s ease";
  simLog.style.transition  = "opacity 0.3s ease";

  setInterval(cycle, 5000);
}
