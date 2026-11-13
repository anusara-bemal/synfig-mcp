/**
 * Synfig MCP Website — Interactive Developer Experience
 * Vanilla JS · Zero External Libraries · Zero Runtime Deps
 */

// ============================================================
// Synfig MCP Tool Catalog (generated — do not edit by hand)
//   Regenerate: uv run python scripts/generate_website_catalog.py
// ============================================================
const TOOLS_CATALOG = [
  // Generated from the live server registry by scripts/generate_website_catalog.py.
  { name: "anim_animate_param", profiles: ["anim", "all"], desc: "Define a full parameter animation trajectory using a batch of waypoints in ONE single undo step.", params: "(doc_id: string, layer_id: string, param_name: string, waypoints: array)" },
  { name: "anim_interpolation_set", profiles: ["anim", "all"], desc: "Set default canvas waypoint interpolation or change interpolation on existing waypoints.", params: "(doc_id: string, interpolation: string, layer_id?: any, param_name?: any)" },
  { name: "anim_keyframe_add", profiles: ["anim", "all"], desc: "Add a keyframe at the specified time to lock parameter values into an animation pose.", params: "(doc_id: string, time: number, description?: string, active?: boolean, canvas_path?: string)" },
  { name: "anim_keyframe_list", profiles: ["anim", "all"], desc: "List all keyframes defined on the timeline.", params: "(doc_id?: string, canvas_path?: string)" },
  { name: "anim_keyframe_remove", profiles: ["anim", "all"], desc: "Delete a keyframe at the specified time.", params: "(doc_id: string, time: number, canvas_path?: string)" },
  { name: "anim_time_get", profiles: ["anim", "all"], desc: "Get the current timeline cursor / playhead position in seconds.", params: "(doc_id?: string)" },
  { name: "anim_time_set", profiles: ["anim", "all"], desc: "Seek the timeline cursor / playhead to a specific time in seconds.", params: "(doc_id: string, time: number)" },
  { name: "anim_waypoint_list", profiles: ["anim", "all"], desc: "List the waypoints of an animated parameter.", params: "(doc_id: string, layer_id: string, param_name: string)" },
  { name: "anim_waypoint_remove", profiles: ["anim", "all"], desc: "Remove a waypoint from a layer parameter at a given time.", params: "(doc_id: string, layer_id: string, param_name: string, time: number)" },
  { name: "anim_waypoint_set", profiles: ["anim", "all"], desc: "Insert or update a waypoint for a layer parameter at a specific timeline timestamp.", params: "(doc_id: string, layer_id: string, param_name: string, time: number, value: any, interpolation_in?: string, interpolation_out?: string)" },
  { name: "asset_download", profiles: ["assets", "all"], desc: "Download and verify licensed asset: evaluates license policy, SSRF checks, sanitizes SVG/raster, hashes SHA-256.", params: "(asset_id: string, provider?: string)" },
  { name: "asset_import_local", profiles: ["assets", "all"], desc: "Register a local file in the project provenance manifest with mandatory rights declaration.", params: "(file_path: string, rights: string, title?: string, creator?: string, license_code?: string)" },
  { name: "asset_preview", profiles: ["assets", "all"], desc: "Fetch a small thumbnail preview image of an asset in base64.", params: "(asset_id: string, provider?: string)" },
  { name: "asset_search", profiles: ["assets", "all"], desc: "Search permitted open-license asset providers returning compact text metadata.", params: "(query: string, provider?: string, license_type?: any, page?: integer)" },
  { name: "canvas_create", profiles: ["rig", "all"], desc: "Create a child canvas (a sub-canvas that group layers can reference).", params: "(doc_id?: string, canvas_id?: string)" },
  { name: "canvas_delete", profiles: ["rig", "all"], desc: "Delete a child canvas and everything inside it.", params: "(doc_id?: string, canvas_id?: string)" },
  { name: "canvas_list", profiles: ["all"], desc: "List all canvas paths in the document (root canvas and nested group/subcanvases).", params: "(doc_id?: string)" },
  { name: "canvas_rename", profiles: ["rig", "all"], desc: "Rename a child canvas.", params: "(doc_id?: string, canvas_id?: string, name?: string)" },
  { name: "canvas_set_properties", profiles: ["rig", "all"], desc: "Change the resolution, frame rate, time range or background colour of a canvas.", params: "(doc_id?: string, canvas_id?: string, width?: any, height?: any, fps?: any, start_time?: any, end_time?: any, background_color?: any)" },
  { name: "character_model_sheet", profiles: ["rig", "all"], desc: "Auto-generate a labeled model/rig sheet (front, three-quarter, side) for one character. descriptor: {id, archetype: humanoid|chibi, height, palette, facing, position, z}.", params: "(descriptor: object, style?: string, width?: integer, height?: integer, dry_run?: boolean)" },
  { name: "character_motion_apply", profiles: ["rig", "all"], desc: "Animate a rigged character: walk, run, idle, talk (loop until end_time), wave, jump, nod, punch (play once), rest, move. move_to={x, y} (canvas pixels) travels there by end_time.", params: "(doc_id?: string, character_id?: string, motion_name?: string, start_time?: number, end_time?: any, speed?: number, move_to?: any)" },
  { name: "character_pose_apply", profiles: ["rig", "all"], desc: "Key a pose on a rigged character: a preset (idle, punch, jump, walk_contact, walk_passing) or explicit joint angles, e.g. angles={\"upper_arm_r\": 120, \"head\": -10} (degrees from rest).", params: "(doc_id?: string, character_id?: string, pose_name?: string, time?: number, angles?: any)" },
  { name: "character_rig_from_parts", profiles: ["rig", "all"], desc: "Assemble a jointed cut-out character from part images (or primitives) in an open document. spec: {doc_id, id, manifest | parts: [{name, file, parent?, pivot?: {fx, fy}, attach?: {fx, fy}, z?}], pos...", params: "(spec: object, dry_run?: boolean)" },
  { name: "doc_close", profiles: ["all"], desc: "Close an open document and unload it from memory.", params: "(doc_id: string, force?: boolean)" },
  { name: "doc_info", profiles: ["core", "anim", "fx", "rig", "assets", "review", "all"], desc: "Get metadata, resolution, framerate, and time bounds for a specific document.", params: "(doc_id?: string)" },
  { name: "doc_list", profiles: ["core", "anim", "fx", "rig", "assets", "review", "all"], desc: "List all currently open or loaded animation documents.", params: "()" },
  { name: "doc_new", profiles: ["core", "all"], desc: "Create a new blank Synfig animation document with specified resolution and framerate.", params: "(width?: integer, height?: integer, fps?: number)" },
  { name: "doc_open", profiles: ["core", "all"], desc: "Open an existing Synfig animation project (.sif, .sifz, or .sfg container).", params: "(file_path: string)" },
  { name: "doc_save", profiles: ["core", "all"], desc: "Save the document to disk in .sif (XML), .sifz (gzip), or .sfg (ZIP container) format.", params: "(doc_id: string, file_path?: any)" },
  { name: "doc_set_properties", profiles: ["all"], desc: "Update canvas resolution, frame rate, time bounds, or name.", params: "(doc_id: string, name?: any, desc?: any, width?: any, height?: any, fps?: any, start_time?: any, end_time?: any)" },
  { name: "doc_set_time_range", profiles: ["anim", "all"], desc: "Set canvas animation playback timeline start time, end time, and framerate.", params: "(doc_id?: string, start_time?: any, end_time?: any, fps?: any)" },
  { name: "health_check", profiles: ["core", "anim", "fx", "rig", "assets", "review", "all"], desc: "Check server readiness, active backend ('live' Synfig Studio vs 'headless' pure-Python SIF engine), and connection status.", params: "()" },
  { name: "history_list", profiles: ["all"], desc: "Query current undo and redo stack depths.", params: "(doc_id?: string)" },
  { name: "history_redo", profiles: ["core", "anim", "fx", "rig", "assets", "review", "all"], desc: "Redo the previously undone action.", params: "(doc_id?: string)" },
  { name: "history_undo", profiles: ["core", "anim", "fx", "rig", "assets", "review", "all"], desc: "Undo the previous action in Studio or Headless mode. Exactly 1 MCP mutating tool call = 1 undo step.", params: "(doc_id?: string)" },
  { name: "import_asset", profiles: ["assets", "all"], desc: "Import an external asset file (e.g. .png, .jpg, .svg, .wav, .ogg) into the canvas.", params: "(doc_id: string, file_path: string, canvas_path?: string)" },
  { name: "layer_add", profiles: ["fx", "all"], desc: "Add a new visual layer (e.g. 'circle', 'rectangle', 'star', 'solid_color', 'text', 'PasteCanvas') to the canvas.", params: "(doc_id: string, layer_type: string, canvas_path?: string, description?: any, params?: any)" },
  { name: "layer_duplicate", profiles: ["fx", "all"], desc: "Duplicate an existing layer, creating an identical copy placed directly above the original.", params: "(doc_id: string, layer_id: string, canvas_path?: string)" },
  { name: "layer_group", profiles: ["fx", "rig", "all"], desc: "Group multiple layers into a PasteCanvas composite layer.", params: "(doc_id: string, layer_ids: array, group_name?: string, canvas_path?: string)" },
  { name: "layer_lower", profiles: ["fx", "all"], desc: "Lower a layer by 1 position (further from camera, depth + 1).", params: "(doc_id: string, layer_id: string, canvas_path?: string)" },
  { name: "layer_raise", profiles: ["fx", "all"], desc: "Raise a layer by 1 position (closer to camera, depth - 1).", params: "(doc_id: string, layer_id: string, canvas_path?: string)" },
  { name: "layer_remove", profiles: ["fx", "all"], desc: "Delete a layer from the composition.", params: "(doc_id: string, layer_id: string, canvas_path?: string)" },
  { name: "layer_reorder", profiles: ["fx", "all"], desc: "Move a layer to a specific visual depth (depth 0 is topmost, in front of all other layers).", params: "(doc_id: string, layer_id: string, new_depth: integer, canvas_path?: string)" },
  { name: "layer_ungroup", profiles: ["fx", "rig", "all"], desc: "Ungroup a PasteCanvas layer, releasing its children into the parent canvas.", params: "(doc_id: string, layer_id: string, canvas_path?: string)" },
  { name: "param_convert", profiles: ["fx", "all"], desc: "Convert a layer parameter into a linkable ValueNode (e.g. 'linear', 'add', 'subtract', 'scale', 'composite', 'sine', 'duplicate', 'range', 'step', 'absolute').", params: "(doc_id: string, layer_id: string, param_name: string, type: string)" },
  { name: "param_export", profiles: ["rig", "all"], desc: "Export a parameter's ValueNode to the canvas value node library for sharing across layers.", params: "(doc_id: string, layer_id: string, param_name: string, name: string)" },
  { name: "param_get", profiles: ["anim", "fx", "all"], desc: "Read the typed value of a specific parameter on a layer.", params: "(doc_id: string, layer_id: string, param_name: string, canvas_path?: string)" },
  { name: "param_link", profiles: ["anim", "fx", "rig", "all"], desc: "Link a parameter to an exported ValueNode so it follows the shared value.", params: "(doc_id: string, layer_id: string, param_name: string, link_id: string)" },
  { name: "param_list", profiles: ["all"], desc: "List every parameter of a layer with its current value.", params: "(doc_id: string, layer_id: string, canvas_path?: string)" },
  { name: "param_set", profiles: ["anim", "fx", "all"], desc: "Set or update the value of a parameter on a layer.", params: "(doc_id: string, layer_id: string, param_name: string, value: any, canvas_path?: string)" },
  { name: "param_unexport", profiles: ["rig", "all"], desc: "Unexport a previously exported ValueNode from the canvas library.", params: "(doc_id: string, name: string)" },
  { name: "procedural_asset_generate", profiles: ["assets", "all"], desc: "Generate one procedural vector asset and add it to a document. kind: background | prop | texture; generator: see procedural_asset_list. position/height are canvas pixels (props only).", params: "(doc_id: string, kind?: string, generator?: string, seed?: integer, position?: any, height?: any, style?: any, dry_run?: boolean)" },
  { name: "procedural_asset_list", profiles: ["assets", "all"], desc: "List the built-in procedural asset generators (offline, IP-safe).", params: "()" },
  { name: "produce_anime_project", profiles: ["all"], desc: "Build a whole anime-style project from one brief: storyboard, rigged characters, assets, assembled scene, style stack, render and review. brief: {title, style, width, height, fps, duration, seed, s...", params: "(brief: object, dry_run?: boolean, stages?: any, resume_from?: any)" },
  { name: "production_plan", profiles: ["all"], desc: "Dry-run the production pipeline: report the stages and layer counts without building. brief: same shape as produce_anime_project (see synfig_help('production')).", params: "(brief: object)" },
  { name: "recipe_apply", profiles: ["fx", "all"], desc: "Apply a parameterized visual effect recipe atomically as a single undo step.", params: "(doc_id?: string, name?: string, params?: any, target_layer_or_group?: any, dry_run?: boolean)" },
  { name: "recipe_info", profiles: ["fx", "all"], desc: "Get parameter specification, defaults, and usage notes for a named recipe.", params: "(name: string)" },
  { name: "recipe_list", profiles: ["fx", "all"], desc: "List all parameterized anime effects recipes (speed lines, vignette, grain, blur, etc.).", params: "()" },
  { name: "render_cancel", profiles: ["review", "all"], desc: "Cancel an active in-flight render job by its job_id.", params: "(job_id: string)" },
  { name: "render_contact_sheet", profiles: ["review", "all"], desc: "Render selected keyframe timestamps into a visual contact sheet / storyboard grid image.", params: "(doc_id: string, output_path: string, cols?: integer, rows?: integer, width?: any, height?: any, start_time?: any, end_time?: any)" },
  { name: "render_frame", profiles: ["core", "review", "all"], desc: "Render a single frame of the animation to an image file (PNG, JPEG, BMP, GIF, PPM).", params: "(doc_id: string, output_path: string, time?: number, width?: any, height?: any, target?: string)" },
  { name: "render_result", profiles: ["review", "all"], desc: "Retrieve final output frames for a completed render job.", params: "(job_id: string)" },
  { name: "render_sequence", profiles: ["review", "all"], desc: "Render an image sequence across an animation time range using the rendering pipeline.", params: "(doc_id: string, output_dir: string, start_time?: any, end_time?: any, fps?: any, width?: any, height?: any, target?: string, job_id?: any)" },
  { name: "render_start", profiles: ["review", "all"], desc: "Start an asynchronous animation render job and immediately return a job_id.", params: "(doc_id: string, output_dir: string, start_time?: any, end_time?: any, fps?: any, width?: any, height?: any, target?: string)" },
  { name: "render_status", profiles: ["review", "all"], desc: "Query the execution status and progress of an asynchronous render job.", params: "(job_id: string)" },
  { name: "render_video", profiles: ["review", "all"], desc: "Render an animation time range and compile directly to a video file (.mp4 or .gif).", params: "(doc_id: string, output_path: string, start_time?: any, end_time?: any, fps?: any, width?: any, height?: any)" },
  { name: "review_compare", profiles: ["review", "all"], desc: "Compare two animation iterations/frames with side-by-side visual diff heatmap and SSIM score.", params: "(doc_id_a?: string, time_a?: number, doc_id_b?: string, time_b?: number, width?: integer, height?: integer)" },
  { name: "review_frame", profiles: ["review", "all"], desc: "Render a single frame paired with objective vision metrics (clipping, safe-area, empty-check, palette).", params: "(doc_id?: string, time?: number, focus_region?: any, width?: integer, height?: integer)" },
  { name: "review_sequence", profiles: ["review", "all"], desc: "Render a sequence of frames compiled into a single contact-sheet image with motion and strobe metrics.", params: "(doc_id?: string, start_time?: number, end_time?: number, frame_count?: integer, width?: integer, height?: integer)" },
  { name: "rig_bone_add", profiles: ["rig", "all"], desc: "Add a bone to a skeleton layer (Synfig's cut-out rigging primitive).", params: "(doc_id?: string, layer_id?: string, time?: number, origin_x?: number, origin_y?: number, angle?: number, width?: number, tip_width?: number, parent_index?: integer)" },
  { name: "rig_sheet_slice", profiles: ["rig", "assets", "all"], desc: "Cut a character rig sheet (one image, many body parts) into one transparent PNG per part. Call once without names and look at preview_base64 (numbered boxes), then call again with names={\"1\": \"head...", params: "(file_path: string, names?: any, output_dir?: any, min_area?: any, merge_gap?: integer, bg_tolerance?: integer, preview?: boolean)" },
  { name: "scene_auto_build", profiles: ["rig", "all"], desc: "Build a whole animated shot in one call: background, rigged cut-out characters, props, camera moves and audio. One undo step; everything is validated before the document changes. spec: {width, heig...", params: "(spec: object, dry_run?: boolean)" },
  { name: "scene_build", profiles: ["core", "all"], desc: "Apply declarative scene build spec. Spec: {doc_id, layers: [{id, type, params}], groups}. Layer 'id' required. Image paths host-resolved or via SYNFIG_MCP_PATH_MAPPING.", params: "(spec: object, dry_run?: boolean)" },
  { name: "scene_export_spec", profiles: ["core", "all"], desc: "Export current scene state into a declarative SceneBuildSpec JSON.", params: "(doc_id?: string, scope?: string, fields?: any)" },
  { name: "scene_summary", profiles: ["core", "anim", "fx", "rig", "assets", "review", "all"], desc: "Get a token-bounded structural summary of canvas size, framerate, duration, and layer hierarchy.", params: "(doc_id?: string, budget_tokens?: integer)" },
  { name: "scene_tree", profiles: ["all"], desc: "Get the full visual hierarchy of layers in depth order (topmost layer at index 0).", params: "(doc_id?: string, canvas_path?: string)" },
  { name: "schema_get_layer", profiles: ["all"], desc: "Get parameter schemas, default values, and hints for a specific layer type.", params: "(layer_type: string)" },
  { name: "schema_list_layers", profiles: ["all"], desc: "List all layer types supported by the installed Synfig build (e.g. 'circle', 'rectangle', 'star', 'text', 'blur', 'outline').", params: "()" },
  { name: "schema_list_renderers", profiles: ["all"], desc: "List available rendering engines (e.g. 'software', 'software-draft', 'safe').", params: "()" },
  { name: "schema_list_targets", profiles: ["all"], desc: "List supported render output targets (e.g. 'png', 'jpeg', 'bmp', 'gif', 'ffmpeg').", params: "()" },
  { name: "schema_list_valuenodes", profiles: ["all"], desc: "List supported valuenode link converter types (e.g. 'composite', 'add', 'sine', 'random').", params: "()" },
  { name: "selection_get", profiles: ["rig", "all"], desc: "Get the list of currently selected layer IDs in Studio.", params: "(doc_id?: string)" },
  { name: "selection_set", profiles: ["rig", "all"], desc: "Set the active layer selection in Studio.", params: "(doc_id: string, layer_ids: array)" },
  { name: "sprite_slice", profiles: ["rig", "assets", "all"], desc: "Slice a sprite sheet or layered raster into named, rig-ready transparent part PNGs. strategy: grid (rows x cols), alpha (connected components) or trim (tight alpha boxes); pass rectangles [{name, x...", params: "(source: string, output_dir: string, strategy?: string, rows?: integer, cols?: integer, rectangles?: any, bg_tolerance?: integer, padding?: integer, dry_run?: boolean)" },
  { name: "storyboard_from_script", profiles: ["rig", "all"], desc: "Assemble a multi-shot animatic timeline from a structured storyboard script.", params: "(spec: object, dry_run?: boolean)" },
  { name: "style_apply", profiles: ["fx", "all"], desc: "Apply a complete anime aesthetic style stack (grading, grain, vignette, recipes) atomically.", params: "(doc_id?: string, name?: string, dry_run?: boolean)" },
  { name: "style_get", profiles: ["fx", "all"], desc: "Get detailed configuration of a generic style preset.", params: "(name: string)" },
  { name: "style_list", profiles: ["fx", "all"], desc: "List all generic anime style presets (shonen_action, dark_fantasy, supernatural_noir, etc.).", params: "()" },
  { name: "synfig_help", profiles: ["core", "anim", "fx", "rig", "assets", "review", "all"], desc: "Get detailed guidance on Synfig MCP topics (overview, profiles, declarative_build, animation, characters, review).", params: "(topic?: string)" },
];
// END GENERATED CATALOG

// ============================================================
// Live capability counts (generated — do not edit by hand)
// ============================================================
const MCP_STATS = {
  total: 89,
  profiles: { core: 13, anim: 21, fx: 25, rig: 27, assets: 16, review: 18 },
};
// END GENERATED STATS

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
      const matchProfile =
        currentProfile === "all" || tool.profiles.includes(currentProfile);
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
      const specific = tool.profiles.filter(p => p !== "all");
      const badge = specific.length >= 6 ? "all" : specific.join(" · ");
      card.className = "tool-item-card";
      card.innerHTML = `
        <div>
          <div class="tool-card-head">
            <span class="tool-fn-name">${escapeHtml(tool.name)}</span>
            <span class="tool-category-badge">${escapeHtml(badge)}</span>
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
